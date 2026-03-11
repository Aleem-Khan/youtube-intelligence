@echo off
echo ============================================================
echo   THE GIANT -- Installing Faceless Detector Dependencies
echo ============================================================
echo.
echo Step 1: Activating virtual environment...
call venv\Scripts\activate

echo.
echo Step 2: Installing OpenCV for thumbnail/video face detection...
pip install opencv-python --break-system-packages

echo.
echo Step 3: Installing HuggingFace Transformers + PyTorch (CPU)...
pip install transformers torch --break-system-packages

echo.
echo Step 4: Installing numpy...
pip install numpy --break-system-packages

echo.
echo ============================================================
echo   Done! Now test the detector by running:
echo   python faceless_detector.py
echo ============================================================
pause
