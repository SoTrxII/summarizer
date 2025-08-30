import logging
from json import dumps
from pathlib import Path
from typing import List

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatHistoryAgentThread

from summarizer.models.scene import Scene

from .models import CampaignSummary, EpisodeSummary, SceneSummary, SummaryArguments
from .utils.yaml import load_agent


class Summarizer:
    """
    Summarize different part of a tabletop role-playing game session.
    """

    def __init__(self, kernel: Kernel, args: SummaryArguments):
        self.kernel = kernel
        self.args = args

    async def scene(self, scene: Scene, previous_summary: SceneSummary | None = None) -> SceneSummary:
        """
        Summarize a scene. A scene is a specific moment with a theme.
        :param scene: The scene to summarize.
        :param previous_summary: The previous scene summary, if any. It is used for context.
        :return: The summary of the scene.
        """
        prompt_path = Path(__file__).parent / "agents" / "scene.yaml"
        agent = load_agent(prompt_path, self.kernel, SceneSummary, self.args)

        thread = ChatHistoryAgentThread()
        thread._chat_history.add_user_message(
            f"PREVIOUS SCENE SUMMARY: {previous_summary or 'NO PREVIOUS SUMMARY'}"
        )

        res = await agent.get_response(f"SCENE TO SUMMARIZE\n:{scene}", thread=thread)
        try:
            return SceneSummary.model_validate_json(res.message.content)
        except Exception as e:
            logging.error(
                f"Error validating scene summary. Content filtering ?: {e}")
            # TODO : Handle a None to bypass the scene
            raise

    async def episode(self, scenes_summaries: List[SceneSummary], previous_summary: EpisodeSummary | None = None) -> EpisodeSummary:
        """
        Summarize an episode. An episode is a collection of scenes with a common theme.
        :param scenes_summaries: The summaries of the scenes in the episode.
        :param previous_summary: The previous episode summary, if any. It is used for context.
        :return: The summary of the episode.
        """
        prompt_path = Path(__file__).parent / "agents" / "episode.yaml"
        agent = load_agent(prompt_path, self.kernel, EpisodeSummary, self.args)

        thread = ChatHistoryAgentThread()
        thread._chat_history.add_user_message(
            f"PREVIOUS EPISODE SUMMARY: {previous_summary or 'NO PREVIOUS SUMMARY'}"
        )

        res = await agent.get_response(f"SCENES TO SUMMARIZE\n:{dumps([s.model_dump() for s in scenes_summaries])}", thread=thread)
        return EpisodeSummary.model_validate_json(res.message.content)

    async def campaign(self, episodes_summaries: List[EpisodeSummary], previous_summary: CampaignSummary | None = None) -> CampaignSummary:
        """
        Summarize a campaign. A campaign is a series of episodes with a common theme.
        :param episodes_summaries: The summaries of the episodes in the campaign.
        :param previous_summary: The previous campaign summary, if any. It is used for context.
        :return: The summary of the campaign.
        """
        prompt_path = Path(__file__).parent / "agents" / "campaign.yaml"
        agent = load_agent(
            prompt_path,
            self.kernel,
            CampaignSummary,
            self.args
        )

        thread = ChatHistoryAgentThread()
        thread._chat_history.add_user_message(
            f"PREVIOUS CAMPAIGN SUMMARY: {previous_summary or 'NO PREVIOUS SUMMARY'}"
        )

        episodes_data = [episode.model_dump()
                         for episode in episodes_summaries]
        res = await agent.get_response(f"EPISODES TO SUMMARIZE\n:{dumps(episodes_data)}", thread=thread)
        return CampaignSummary.model_validate_json(res.message.content)
