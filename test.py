from deepface import DeepFace

DeepFace.stream(
    db_path="./dataset",
    source=1,
    enable_face_analysis=False,
    time_threshold=0,
    frame_threshold=0,
    detector_backend="opencv"

)
