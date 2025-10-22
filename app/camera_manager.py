"""Camera manager to maintain persistent connection to camera via gphoto2."""

import gphoto2 as gp
import logging
from typing import Optional, Dict, Any, Tuple
from io import BytesIO

logger = logging.getLogger(__name__)


class CameraManager:
    """Manages persistent camera connection and capture operations."""
    
    def __init__(self):
        self.camera: Optional[gp.Camera] = None
        self.context = gp.Context()
        self._camera_model: Optional[str] = None
        
    def connect(self) -> bool:
        """
        Initialize and connect to the camera.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.camera is not None:
                logger.info("Camera already connected")
                return True
                
            logger.info("Initializing camera connection...")
            self.camera = gp.Camera()
            self.camera.init(self.context)
            
            # Get camera summary to verify connection
            summary = self.camera.get_summary(self.context)
            abilities = self.camera.get_abilities()
            self._camera_model = abilities.model
            
            logger.info(f"Camera connected successfully: {self._camera_model}")
            logger.info(f"Summary: {summary.text[:100]}...")
            return True
            
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to connect to camera: {e}")
            self.camera = None
            return False
    
    def disconnect(self):
        """Close the camera connection."""
        if self.camera is not None:
            try:
                self.camera.exit(self.context)
                logger.info("Camera disconnected")
            except gp.GPhoto2Error as e:
                logger.error(f"Error disconnecting camera: {e}")
            finally:
                self.camera = None
    
    def is_connected(self) -> bool:
        """Check if camera is connected."""
        return self.camera is not None
    
    def get_camera_model(self) -> Optional[str]:
        """Get the camera model name."""
        return self._camera_model
    
    def get_raw_extension(self) -> str:
        """
        Determine the RAW file extension based on camera manufacturer.
        
        Returns:
            str: File extension for RAW format (e.g., 'nef', 'cr2', 'arw')
        """
        if not self._camera_model:
            return 'raw'
        
        model_lower = self._camera_model.lower()
        
        # Nikon cameras use NEF
        if 'nikon' in model_lower:
            return 'nef'
        # Canon cameras use CR2 or CR3
        elif 'canon' in model_lower:
            if 'eos r' in model_lower or 'eos-1d x mark iii' in model_lower:
                return 'cr3'  # Newer Canon models
            return 'cr2'
        # Sony cameras use ARW
        elif 'sony' in model_lower:
            return 'arw'
        # Fujifilm cameras use RAF
        elif 'fuji' in model_lower:
            return 'raf'
        # Olympus cameras use ORF
        elif 'olympus' in model_lower:
            return 'orf'
        # Panasonic cameras use RW2
        elif 'panasonic' in model_lower:
            return 'rw2'
        # Pentax cameras use PEF or DNG
        elif 'pentax' in model_lower:
            return 'pef'
        # Leica cameras use DNG
        elif 'leica' in model_lower:
            return 'dng'
        # Hasselblad cameras use 3FR
        elif 'hasselblad' in model_lower:
            return '3fr'
        # Phase One cameras use IIQ
        elif 'phase one' in model_lower:
            return 'iiq'
        else:
            return 'raw'
    
    def set_image_format(self, format_type: str) -> bool:
        """
        Set the camera image format to RAW or JPEG.
        
        Args:
            format_type: 'raw' or 'jpeg'
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Camera not connected")
            return False
        
        format_type = format_type.lower()
        
        try:
            config = self.camera.get_config(self.context)
            
            # Try common setting names for image format
            setting_names = ['imageformat', 'imagequality', 'captureformat', 'imageformatsd']
            
            widget = None
            for setting_name in setting_names:
                try:
                    widget = config.get_child_by_name(setting_name)
                    logger.info(f"Found image format setting: {setting_name}")
                    break
                except gp.GPhoto2Error:
                    continue
            
            if widget is None:
                # Try recursive search
                widget = self._find_widget_recursive(config, 'imageformat')
                if widget is None:
                    logger.warning("Could not find image format setting")
                    return False
            
            # Get available choices
            choices = []
            for i in range(widget.count_choices()):
                choices.append(widget.get_choice(i))
            
            logger.info(f"Available format choices: {choices}")
            
            # Find the best matching choice
            target_value = None
            if format_type == 'raw':
                # Look for RAW options
                for choice in choices:
                    choice_lower = choice.lower()
                    if 'raw' in choice_lower or 'nef' in choice_lower or 'cr2' in choice_lower or 'arw' in choice_lower:
                        target_value = choice
                        break
            elif format_type == 'jpeg' or format_type == 'jpg':
                # Look for JPEG options (prefer highest quality)
                for choice in choices:
                    choice_lower = choice.lower()
                    if 'jpeg' in choice_lower or 'jpg' in choice_lower:
                        if 'fine' in choice_lower or 'large' in choice_lower or 'basic' in choice_lower:
                            target_value = choice
                            # Keep looking for "fine" or "large" options
                            if 'fine' in choice_lower and 'large' in choice_lower:
                                break
            
            if target_value is None:
                logger.error(f"Could not find suitable format option for '{format_type}'")
                return False
            
            # Set the value
            widget.set_value(target_value)
            self.camera.set_config(config, self.context)
            logger.info(f"Set image format to: {target_value}")
            return True
            
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to set image format: {e}")
            return False
    
    def get_config(self) -> Optional[gp.CameraWidget]:
        """
        Get camera configuration.
        
        Returns:
            CameraWidget: Root configuration widget or None
        """
        if not self.is_connected():
            return None
        
        try:
            config = self.camera.get_config(self.context)
            return config
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to get camera config: {e}")
            return None
    
    def set_config_value(self, config_name: str, value: str) -> bool:
        """
        Set a camera configuration value.
        
        Args:
            config_name: Name of the configuration (e.g., 'iso', 'shutterspeed')
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Camera not connected")
            return False
        
        try:
            # Get current config
            config = self.camera.get_config(self.context)
            
            # Try to find the config widget
            try:
                widget = config.get_child_by_name(config_name)
            except gp.GPhoto2Error:
                logger.warning(f"Config '{config_name}' not found, trying case-insensitive search...")
                # Try case-insensitive search
                widget = self._find_widget_recursive(config, config_name.lower())
                if widget is None:
                    logger.error(f"Config '{config_name}' not found in camera settings")
                    return False
            
            # Set the value
            widget.set_value(value)
            
            # Apply the config
            self.camera.set_config(config, self.context)
            logger.info(f"Set camera config: {config_name} = {value}")
            return True
            
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to set config '{config_name}' to '{value}': {e}")
            return False
    
    def _find_widget_recursive(self, widget: gp.CameraWidget, name: str) -> Optional[gp.CameraWidget]:
        """
        Recursively search for a widget by name (case-insensitive).
        
        Args:
            widget: Widget to search in
            name: Name to search for (lowercase)
            
        Returns:
            CameraWidget or None
        """
        try:
            widget_name = widget.get_name()
            if widget_name.lower() == name:
                return widget
        except:
            pass
        
        # Search children
        try:
            for i in range(widget.count_children()):
                child = widget.get_child(i)
                result = self._find_widget_recursive(child, name)
                if result is not None:
                    return result
        except:
            pass
        
        return None
    
    def apply_settings(self, settings: Dict[str, str]) -> Dict[str, bool]:
        """
        Apply multiple camera settings at once.
        
        Args:
            settings: Dictionary of setting names and values
            
        Returns:
            Dictionary with setting names and success status
        """
        results = {}
        for key, value in settings.items():
            results[key] = self.set_config_value(key, value)
        return results
    
    def get_available_settings(self) -> Dict[str, Any]:
        """
        Get all available camera settings with their current values and options.
        
        Returns:
            Dictionary with setting information
        """
        if not self.is_connected():
            return {"error": "Camera not connected"}
        
        try:
            config = self.camera.get_config(self.context)
            settings = {}
            self._extract_settings_recursive(config, settings)
            return settings
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to get available settings: {e}")
            return {"error": str(e)}
    
    def _extract_settings_recursive(self, widget: gp.CameraWidget, settings: dict, prefix: str = ""):
        """
        Recursively extract all settings from config tree.
        
        Args:
            widget: Widget to extract from
            settings: Dictionary to populate
            prefix: Prefix for nested settings
        """
        try:
            widget_type = widget.get_type()
            widget_name = widget.get_name()
            
            # Only extract configurable widgets
            if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU, 
                              gp.GP_WIDGET_TEXT, gp.GP_WIDGET_RANGE,
                              gp.GP_WIDGET_TOGGLE, gp.GP_WIDGET_DATE):
                
                full_name = f"{prefix}.{widget_name}" if prefix else widget_name
                
                try:
                    current_value = widget.get_value()
                    setting_info = {
                        "current": str(current_value),
                        "type": self._get_widget_type_name(widget_type)
                    }
                    
                    # Add choices for radio/menu widgets
                    if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                        choices = []
                        for i in range(widget.count_choices()):
                            choices.append(widget.get_choice(i))
                        setting_info["choices"] = choices
                    
                    # Add range info for range widgets
                    elif widget_type == gp.GP_WIDGET_RANGE:
                        setting_info["range"] = {
                            "min": widget.get_range()[0],
                            "max": widget.get_range()[1],
                            "step": widget.get_range()[2]
                        }
                    
                    settings[widget_name] = setting_info
                except:
                    pass
            
            # Recurse into children
            for i in range(widget.count_children()):
                child = widget.get_child(i)
                self._extract_settings_recursive(child, settings, prefix)
                
        except:
            pass
    
    def _get_widget_type_name(self, widget_type: int) -> str:
        """Get human-readable widget type name."""
        type_map = {
            gp.GP_WIDGET_RADIO: "radio",
            gp.GP_WIDGET_MENU: "menu",
            gp.GP_WIDGET_TEXT: "text",
            gp.GP_WIDGET_RANGE: "range",
            gp.GP_WIDGET_TOGGLE: "toggle",
            gp.GP_WIDGET_DATE: "date"
        }
        return type_map.get(widget_type, "unknown")
    
    def capture_image(self, settings: Optional[Dict[str, str]] = None, 
                     image_format: Optional[str] = None) -> Optional[Tuple[BytesIO, str]]:
        """
        Capture an image from the camera with optional settings.
        
        Args:
            settings: Optional dictionary of camera settings to apply before capture
            image_format: Optional 'raw' or 'jpeg' to set image format
        
        Returns:
            Tuple of (BytesIO, extension) or None if capture failed
        """
        if not self.is_connected():
            logger.error("Camera not connected")
            if not self.connect():
                return None
        
        # Set image format if specified
        if image_format:
            logger.info(f"Setting image format to: {image_format}")
            if not self.set_image_format(image_format):
                logger.warning(f"Could not set image format to {image_format}, continuing with current format")
        
        # Apply settings if provided
        if settings:
            logger.info(f"Applying {len(settings)} camera settings...")
            results = self.apply_settings(settings)
            failed = [k for k, v in results.items() if not v]
            if failed:
                logger.warning(f"Failed to apply settings: {', '.join(failed)}")
        
        try:
            logger.info("Triggering camera capture...")
            
            # Capture image to camera's storage
            file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE, self.context)
            logger.info(f"Image captured: {file_path.folder}/{file_path.name}")
            
            # Create a CameraFile object to receive the file data
            camera_file = gp.CameraFile()
            
            # Download the image file from camera
            self.camera.file_get(
                file_path.folder, 
                file_path.name, 
                gp.GP_FILE_TYPE_NORMAL,
                camera_file,
                self.context
            )
            
            # Get file data
            file_data = camera_file.get_data_and_size()
            image_buffer = BytesIO(file_data)
            
            # Determine file extension from captured filename
            captured_extension = file_path.name.split('.')[-1].lower() if '.' in file_path.name else None
            
            # If we requested RAW format, use camera-specific extension
            if image_format and image_format.lower() == 'raw' and captured_extension:
                extension = captured_extension
            elif captured_extension:
                extension = captured_extension
            else:
                # Fallback to detection by content
                image_buffer.seek(0)
                first_bytes = image_buffer.read(4)
                image_buffer.seek(0)
                
                if first_bytes[:2] == b'\xff\xd8':
                    extension = 'jpg'
                elif first_bytes[:4] == b'\x89PNG':
                    extension = 'png'
                else:
                    extension = self.get_raw_extension()
            
            # Delete the file from camera to free up space
            try:
                self.camera.file_delete(file_path.folder, file_path.name, self.context)
                logger.info("Image deleted from camera storage")
            except gp.GPhoto2Error as e:
                logger.warning(f"Could not delete file from camera: {e}")
            
            logger.info(f"Image downloaded successfully ({len(file_data)} bytes, .{extension})")
            return (image_buffer, extension)
            
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to capture image: {e}")
            return None
    
    def get_camera_info(self) -> dict:
        """
        Get basic camera information.
        
        Returns:
            dict: Camera information
        """
        if not self.is_connected():
            return {"connected": False, "error": "Camera not connected"}
        
        try:
            summary = self.camera.get_summary(self.context)
            abilities = self.camera.get_abilities()
            
            return {
                "connected": True,
                "model": abilities.model,
                "raw_extension": self.get_raw_extension(),
                "summary": summary.text
            }
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to get camera info: {e}")
            return {"connected": True, "error": str(e)}
