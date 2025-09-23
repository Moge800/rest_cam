from rest_cam.rest_api import main


if __name__ == "__main__":
    SERVER_PORT = 8000
    CAMERA_IDS = [0]

    main(SERVER_PORT, CAMERA_IDS)
