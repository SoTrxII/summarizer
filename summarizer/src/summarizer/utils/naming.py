"""
Utility functions for standardizing file naming conventions across the summarizer project.
"""


def get_standardized_filenames(base_name: str) -> tuple[str, str, str]:
    """
    Generate standardized filenames for scenes, scene summaries, and episode summaries.

    This function ensures consistent naming across the project:
    - Scenes files: {base_name}_scenes.json
    - Scene summaries files: {base_name}_scenes_summaries.json  
    - Episode summary files: {base_name}_episode_summary.json

    Args:
        base_name: The base name (e.g., "10m", "10m_sample2")

    Returns:
        tuple: (scenes_file, scene_summaries_file, episode_summary_file)
    """
    scenes_file = f"{base_name}_scenes.json"
    scene_summaries_file = f"{base_name}_scenes_summaries.json"
    episode_summary_file = f"{base_name}_episode_summary.json"
    return scenes_file, scene_summaries_file, episode_summary_file


def get_base_name_from_scenes_file(scenes_file: str) -> str:
    """
    Extract the base name from a scenes filename.

    Args:
        scenes_file: The scenes filename (e.g., "10m_scenes.json")

    Returns:
        str: The base name (e.g., "10m")
    """
    if scenes_file.endswith("_scenes.json"):
        return scenes_file[:-12]  # Remove "_scenes.json"
    else:
        # Fallback: remove .json extension
        return scenes_file[:-5] if scenes_file.endswith(".json") else scenes_file


def get_base_name_from_summaries_file(summaries_file: str) -> str:
    """
    Extract the base name from a scene summaries filename.

    Args:
        summaries_file: The scene summaries filename (e.g., "10m_scenes_summaries.json")

    Returns:
        str: The base name (e.g., "10m")
    """
    if summaries_file.endswith("_scenes_summaries.json"):
        return summaries_file[:-21]  # Remove "_scenes_summaries.json"
    else:
        # Fallback: remove .json extension
        return summaries_file[:-5] if summaries_file.endswith(".json") else summaries_file
