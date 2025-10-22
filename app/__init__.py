"""Flask application for gphoto2 camera control."""

from .camera_server import create_app

__all__ = ['create_app']
