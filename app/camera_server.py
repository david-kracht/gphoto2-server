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
                "/preview": "Live camera preview stream (MJPEG format)",
                "/preview-page": "HTML page to view the live preview",
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
    
    @app.route('/preview')
    def preview():
        """
        Live camera preview stream as MJPEG.
        
        Returns:
            Response: MJPEG stream (multipart/x-mixed-replace)
        """
        def generate():
            """Generator function that yields preview frames."""
            import time
            
            # Register this stream
            camera_manager.start_preview_stream()
            
            frame_count = 0
            error_count = 0
            max_errors = 3
            
            try:
                while True:
                    frame = camera_manager.capture_preview()
                    
                    if frame is None:
                        error_count += 1
                        logger.warning(f"Failed to capture preview frame (attempt {error_count}/{max_errors})")
                        
                        if error_count >= max_errors:
                            logger.error("Too many preview errors, stopping stream")
                            break
                        
                        # Wait a bit before retrying
                        time.sleep(0.5)
                        continue
                    
                    # Reset error counter on success
                    error_count = 0
                    frame_count += 1
                    
                    # Log first frame details for debugging
                    if frame_count == 1:
                        logger.info(f"First frame: {len(frame)} bytes, starts with {frame[:4].hex()}, ends with {frame[-4:].hex()}")
                    
                    # Yield frame in multipart format with Content-Length
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n'
                        b'Content-Length: ' + str(len(frame)).encode('utf-8') + b'\r\n'
                        b'\r\n' + frame + b'\r\n'
                    )
                    
                    # Small delay to control frame rate (~30 fps max)
                    time.sleep(0.033)
                    
            except GeneratorExit:
                logger.info(f"Preview stream closed by client (sent {frame_count} frames)")
                camera_manager.end_preview_stream()
            except Exception as e:
                logger.error(f"Error in preview stream: {e}")
                camera_manager.end_preview_stream()
        
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/preview-page')
    def preview_page():
        """HTML page to view the live preview stream."""
        html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Camera Live Preview</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #1a1a1a; color: #ffffff; display: flex; flex-direction: column; align-items: center; }
        h1 { color: #4CAF50; margin-bottom: 20px; }
        .preview-container { max-width: 90%; background-color: #2a2a2a; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
        #preview-stream { width: 100%; height: auto; border: 2px solid #4CAF50; border-radius: 4px; }
        .info { margin-top: 20px; padding: 15px; background-color: #333; border-radius: 4px; }
        .status { display: inline-block; padding: 5px 10px; border-radius: 4px; font-weight: bold; margin-left: 10px; }
        .status.connected { background-color: #4CAF50; color: white; }
        .status.disconnected { background-color: #f44336; color: white; }
    </style>
</head>
<body>
    <h1>📷 Camera Live Preview</h1>
    <div class="preview-container">
        <img id="preview-stream" src="/preview" alt="Camera Preview Stream">
    </div>
    <div class="info">
        <p><strong>Stream Status:</strong> <span id="status" class="status">Checking...</span></p>
        <p><strong>Endpoint:</strong> <code>/preview</code></p>
        <p><strong>Format:</strong> MJPEG (multipart/x-mixed-replace)</p>
    </div>
    <script>
        const img = document.getElementById("preview-stream");
        const status = document.getElementById("status");
        img.onload = function() { status.textContent = "Connected"; status.className = "status connected"; };
        img.onerror = function() { status.textContent = "Disconnected"; status.className = "status disconnected"; setTimeout(() => { img.src = "/preview?" + new Date().getTime(); }, 3000); };
        fetch("/status").then(response => response.json()).then(data => { if (data.connected) { status.textContent = "Camera Ready"; status.className = "status connected"; } else { status.textContent = "Camera Not Connected"; status.className = "status disconnected"; } }).catch(err => { status.textContent = "Server Error"; status.className = "status disconnected"; });
    </script>
</body>
</html>"""
        return html

    @app.route('/status')
    def status():
        """Check camera connection status."""
        is_connected = camera_manager.is_connected()
        return jsonify({
            "connected": is_connected,
            "active_preview_streams": camera_manager.get_active_streams(),
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
        Flexible config endpoint - READ or WRITE based on parameters.
        
        NO parameters → READ (return current settings)
        WITH parameters → WRITE (set settings)
        
        Works with both GET (URL params) and POST (JSON body).
        
        Returns:
            JSON with configuration info or results
        """
        # Get parameters from either URL (GET) or JSON body (POST)
        if request.method == 'GET':
            params = request.args.to_dict()
        else:  # POST
            params = request.get_json() if request.is_json else {}
        
        # NO parameters → READ mode
        if not params:
            settings = camera_manager.get_available_settings()
            return jsonify({
                "mode": "read",
                "count": len(settings),
                "settings": settings
            })
        
        # WITH parameters → WRITE mode
        logger.info(f"Config WRITE request with {len(params)} settings")
        results = camera_manager.apply_settings(params)
        success_count = sum(1 for v in results.values() if v)
        
        return jsonify({
            "mode": "write",
            "success": success_count == len(params),
            "applied": success_count,
            "total": len(params),
            "results": results
        })
    
    @app.route('/preview/settings', methods=['GET', 'POST'])
    def preview_settings():
        """
        Flexible preview settings endpoint - change settings during live preview.
        
        NO parameters → READ (return current settings)
        WITH parameters → WRITE (set settings)
        
        Works with both GET (URL params) and POST (JSON body).
        Can be used while preview stream is active.
        
        Returns:
            JSON with settings info or results
        """
        active_streams = camera_manager.get_active_streams()
        
        # Get parameters from either URL (GET) or JSON body (POST)
        if request.method == 'GET':
            params = request.args.to_dict()
        else:  # POST
            params = request.get_json() if request.is_json else {}
        
        # NO parameters → READ mode
        if not params:
            settings = camera_manager.get_available_settings()
            return jsonify({
                "mode": "read",
                "active_streams": active_streams,
                "settings": settings
            })
        
        # WITH parameters → WRITE mode
        logger.info(f"Preview settings WRITE request with {len(params)} settings (active streams: {active_streams})")
        results = camera_manager.apply_settings(params)
        success_count = sum(1 for v in results.values() if v)
        
        return jsonify({
            "mode": "write",
            "success": success_count == len(params),
            "applied": success_count,
            "total": len(params),
            "results": results,
            "active_streams": active_streams
        })
    
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
