"""Flask server application for gphoto2 camera control."""

from flask import Flask, send_file, jsonify, Response, request
import logging
from datetime import datetime
from .camera_manager import CameraManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global camera manager instance
camera_manager = CameraManager()


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        """Root endpoint with API information."""
        return jsonify({
            "service": "gphoto2 Camera Server",
            "version": "1.1.0",
            "endpoints": {
                "/": "This help message",
                "/status": "Get camera connection status",
                "/capture": "Capture and download a photo (GET request with optional parameters)",
                "/info": "Get camera information including RAW format",
                "/settings": "Get all available camera settings with current values and options",
                "/config": "Get or set camera configuration (GET to view, POST with JSON to set)"
            },
            "examples": {
                "capture_raw": "/capture?format=raw",
                "capture_jpeg": "/capture?format=jpeg",
                "capture_raw_with_settings": "/capture?format=raw&iso=800&shutterspeed=1/200",
                "capture_jpeg_with_iso": "/capture?format=jpeg&iso=400",
                "get_settings": "/settings",
                "simple_capture": "/capture"
            },
            "parameters": {
                "format": "Image format: 'raw' (camera-specific RAW format) or 'jpeg'",
                "other": "Any camera setting (iso, shutterspeed, aperture, focusmode, whitebalance, etc.)"
            }
        })
    
    @app.route('/status')
    def status():
        """Check camera connection status."""
        is_connected = camera_manager.is_connected()
        return jsonify({
            "connected": is_connected,
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route('/capture')
    def capture():
        """
        Capture a photo and initiate browser download.
        
        Query Parameters:
            format: 'raw' or 'jpeg' (optional)
            Any camera setting name with its value (e.g., ?iso=800&shutterspeed=1/200)
        
        Returns:
            Response: Image file (RAW/JPEG) or error message
        """
        logger.info("Capture request received")
        
        # Extract format parameter
        image_format = request.args.get('format', None)
        
        # Extract all other query parameters as camera settings
        settings = {}
        for key, value in request.args.items():
            if key.lower() != 'format':  # Skip format parameter
                settings[key] = value
                logger.info(f"Parameter: {key} = {value}")
        
        if image_format:
            logger.info(f"Requested format: {image_format}")
        
        # Capture image with settings and format
        result = camera_manager.capture_image(
            settings=settings if settings else None,
            image_format=image_format
        )
        
        if result is None:
            logger.error("Image capture failed")
            return jsonify({
                "error": "Failed to capture image",
                "message": "Check camera connection and settings"
            }), 500
        
        image_buffer, extension = result
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.{extension}"
        
        # Determine mimetype based on extension
        mimetype_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'nef': 'image/x-nikon-nef',
            'cr2': 'image/x-canon-cr2',
            'cr3': 'image/x-canon-cr3',
            'arw': 'image/x-sony-arw',
            'raf': 'image/x-fuji-raf',
            'orf': 'image/x-olympus-orf',
            'rw2': 'image/x-panasonic-rw2',
            'pef': 'image/x-pentax-pef',
            'dng': 'image/x-adobe-dng',
            '3fr': 'image/x-hasselblad-3fr',
            'iiq': 'image/x-phaseone-iiq'
        }
        mimetype = mimetype_map.get(extension, 'application/octet-stream')
        
        logger.info(f"Sending image: {filename} (type: {mimetype})")
        
        # Send file with download headers
        return send_file(
            image_buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    
    @app.route('/info')
    def info():
        """Get camera information."""
        camera_info = camera_manager.get_camera_info()
        return jsonify(camera_info)
    
    @app.route('/settings')
    def get_settings():
        """
        Get all available camera settings with their current values and options.
        
        Returns:
            JSON with all configurable camera settings
        """
        logger.info("Settings request received")
        settings = camera_manager.get_available_settings()
        
        if "error" in settings:
            return jsonify(settings), 500
        
        return jsonify({
            "count": len(settings),
            "settings": settings,
            "usage": "Use setting names as query parameters in /capture endpoint",
            "example": "/capture?format=raw&iso=800&shutterspeed=1/200"
        })
    
    @app.route('/config', methods=['GET', 'POST'])
    def config():
        """
        Get or set camera configuration.
        
        GET: Returns all available settings
        POST: Set multiple settings (send JSON body with setting: value pairs)
        
        Returns:
            JSON with configuration info or results
        """
        if request.method == 'GET':
            settings = camera_manager.get_available_settings()
            return jsonify(settings)
        
        elif request.method == 'POST':
            if not request.is_json:
                return jsonify({
                    "error": "Content-Type must be application/json"
                }), 400
            
            settings = request.get_json()
            logger.info(f"Config POST request with {len(settings)} settings")
            
            results = camera_manager.apply_settings(settings)
            
            success_count = sum(1 for v in results.values() if v)
            
            return jsonify({
                "applied": success_count,
                "total": len(settings),
                "results": results
            })
    
    @app.before_request
    def ensure_camera_connected():
        """Ensure camera is connected before handling requests."""
        # Skip connection check for root endpoint
        if request.endpoint == 'index':
            return
        
        if not camera_manager.is_connected():
            logger.info("Camera not connected, attempting to connect...")
            if not camera_manager.connect():
                logger.error("Failed to establish camera connection")
    
    @app.teardown_appcontext
    def cleanup(exception=None):
        """Cleanup on application shutdown."""
        if exception:
            logger.error(f"Application error: {exception}")
    
    return app


def main():
    """Main entry point for running the server."""
    logger.info("Starting gphoto2 Camera Server...")
    
    # Initialize camera connection
    if camera_manager.connect():
        logger.info("Camera connected successfully")
        model = camera_manager.get_camera_model()
        raw_ext = camera_manager.get_raw_extension()
        logger.info(f"Camera model: {model}, RAW format: .{raw_ext}")
    else:
        logger.warning("Camera not connected at startup - will retry on first request")
    
    try:
        # Create and run Flask app
        app = create_app()
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        # Ensure camera is disconnected on shutdown
        logger.info("Shutting down server...")
        camera_manager.disconnect()


if __name__ == '__main__':
    main()
