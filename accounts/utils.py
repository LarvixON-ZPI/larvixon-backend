import os
import uuid


def get_user_folder(user) -> str:
    return f"users/{user.pk}/"


def user_video_upload_to(instance, filename):
    # eg. users/1/videos/<hex>/videoname.mp4
    unique_folder = uuid.uuid4().hex
    folder = f"{get_user_folder(instance.user)}/videos/{unique_folder}"
    return os.path.join(folder, filename)


def user_thumbnail_upload_to(instance, filename):
    # eg. users/1/videos/<hex>/videoname.jpg
    video_path = instance.video.name
    folder = os.path.dirname(video_path)
    base_name, _ = os.path.splitext(os.path.basename(video_path))
    thumbnail_name = f"{base_name}_thumb.png"
    return os.path.join(folder, thumbnail_name)


def user_picture_upload_to(instance, filename):
    folder = f"{get_user_folder(instance.user)}/profile"
    return os.path.join(folder, filename)
