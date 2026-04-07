from __future__ import annotations

from features.ai.standalone.qwen3_tts_service import (
    SUPPORTED_SPEAKERS,
    TONE_PRESETS,
    clone_quality_status,
    ensure_unique_profile_name,
    load_profiles,
    profile_by_name,
    profile_names,
    save_profiles,
)


class Qwen3TTSProfileService:
    def load_profiles(self) -> list[dict]:
        return load_profiles()

    def get_profile_choices(self, profiles: list[dict]) -> list[str]:
        return profile_names(profiles)

    def profile_by_name(self, profiles: list[dict], name: str) -> dict:
        return profile_by_name(profiles, name)

    def profile_quality(self, profiles: list[dict], name: str):
        return clone_quality_status(self.profile_by_name(profiles, name))

    def add_profile_template(self, profiles: list[dict]) -> dict:
        return {
            "id": f"profile_{len(profiles) + 1}",
            "name": "New Profile",
            "mode": "custom_voice",
            "speaker": SUPPORTED_SPEAKERS[0],
            "instruct": TONE_PRESETS["natural"],
            "ref_audio": "",
            "ref_text": "",
            "x_vector_only": False,
        }

    def save_profile(
        self,
        profiles: list[dict],
        profile_id: str | None,
        name: str,
        mode: str,
        speaker: str,
        instruct: str,
        ref_audio: str,
        ref_text: str,
    ) -> tuple[bool, list[dict]]:
        name = (name or "").strip() or "Profile"
        if not ensure_unique_profile_name(profiles, name, profile_id):
            return False, profiles

        target = next((item for item in profiles if item["id"] == profile_id), None)
        if target is None:
            target = {
                "id": profile_id or f"profile_{len(profiles)+1}",
                "name": name,
                "mode": mode,
                "speaker": speaker,
                "instruct": instruct,
                "ref_audio": ref_audio,
                "ref_text": ref_text,
                "x_vector_only": False,
            }
            profiles.append(target)
        else:
            target.update(
                {
                    "name": name,
                    "mode": mode,
                    "speaker": speaker,
                    "instruct": instruct,
                    "ref_audio": ref_audio,
                    "ref_text": ref_text,
                }
            )
        save_profiles(profiles)
        return True, profiles

    def delete_profile(self, profiles: list[dict], name: str) -> tuple[bool, list[dict]]:
        if len(profiles) <= 1:
            return False, profiles
        profiles = [item for item in profiles if item["name"] != name]
        save_profiles(profiles)
        return True, profiles

    def profile_to_dict(self, profiles: list[dict], profile_id: str) -> dict | None:
        for item in profiles:
            if item["id"] == profile_id:
                return item
        return None
