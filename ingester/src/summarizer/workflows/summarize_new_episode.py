import logging
from typing import List

from dapr.ext.workflow import DaprWorkflowContext
from opentelemetry import trace

from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence
from summarizer.models.workflow import AudioWorkflowInput, WorkflowInput

from .activities import (
    notify_summary_available,
    publish_scenes_to_lightrag,
    split_into_scenes,
    summarize_campaign,
    summarize_episode,
    summarize_scenes,
    transcribe_audio,
)
from .runtime import wfr

# Get a tracer for this module
tracer = trace.get_tracer(__name__)


@wfr.workflow
def audio_to_summary(ctx: DaprWorkflowContext, input: AudioWorkflowInput):
    with tracer.start_as_current_span("audio_to_summary") as workflow_span:
        with trace.use_span(workflow_span, end_on_exit=False):
            logging.info(
                f"🎵 Starting audio to summary workflow with payload: {input}")

            # Step 1: Transcribe
            logging.info("📝 Step 1: Starting transcription...")
            sentences: List[Sentence] = yield ctx.call_activity(
                transcribe_audio,
                input=input
            )
            logging.info(
                f"✅ Step 1 Complete. Transcribed {len(sentences)} sentences")

            # Step 2: Split into scenes
            logging.info("🎬 Step 2: Starting scene splitting...")
            scenes: List[Scene] = yield ctx.call_activity(split_into_scenes, input={"campaign_id": input["campaign_id"], "episode_id": input["episode_id"], "is_one_shot": input["is_one_shot"]})
            logging.info(f"✅ Step 2 Complete. Split into {len(scenes)} scenes")

            # Step 3: Summarize scenes
            logging.info("📝 Step 3: Starting scene summarization...")
            scenes_summaries = yield ctx.call_activity(
                summarize_scenes,
                input={
                    "scenes": scenes,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"],
                    "is_one_shot": input["is_one_shot"]
                }
            )
            logging.info(
                f"✅ Step 3 Complete. Generated {len(scenes_summaries)} scene summaries")

            # Step 4: Publish scenes to LightRAG
            logging.info("🚀 Step 4: Publishing scenes to LightRAG...")
            yield ctx.call_activity(
                publish_scenes_to_lightrag,
                input={
                    "scenes_summaries": scenes_summaries,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"]
                }
            )
            logging.info("✅ Step 4 Complete. Scenes published to LightRAG")

            # Step 5: Summarize episode
            logging.info("📖 Step 5: Starting episode summarization...")
            episode_summary = yield ctx.call_activity(
                summarize_episode,
                input={
                    "scenes_summaries": scenes_summaries,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"],
                    "is_one_shot": input["is_one_shot"]
                }
            )
            logging.info("✅ Step 5 Complete. Episode summary generated")

            # Step 6: Perform campaign summarization for series episodes (not one-shots)
            if not input["is_one_shot"]:
                logging.info("� Step 6: Starting campaign summarization...")
                yield ctx.call_activity(
                    summarize_campaign,
                    input={
                        "episode_summary": episode_summary,
                        "campaign_id": input["campaign_id"],
                        "episode_id": input["episode_id"],
                        "is_one_shot": input["is_one_shot"]
                    }
                )
                logging.info("✅ Step 6 Complete. Campaign summary generated")
            else:
                logging.info(
                    "⏩ Step 6: Skipping campaign summarization (one-shot episode)")

            # Step 7: Send notification for all episodes
            logging.info("📬 Step 7: Sending summary available notification...")
            yield ctx.call_activity(
                notify_summary_available,
                input={
                    "episode_summary": episode_summary,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"],
                    "is_one_shot": input["is_one_shot"]
                }
            )
            logging.info(
                "✅ Step 7 Complete. Summary available notification sent")


@wfr.workflow
def transcript_to_summary(ctx: DaprWorkflowContext, input: WorkflowInput):
    with tracer.start_as_current_span("transcript_to_summary") as workflow_span:
        with trace.use_span(workflow_span, end_on_exit=False):
            logging.info(
                f"🎵 Starting transcript to summary workflow with campaign_id: {input['campaign_id']}, episode_id: {input['episode_id']}")

            # Step 1: Split into scenes
            logging.info("🎬 Step 1: Starting scene splitting...")
            scenes: List[Scene] = yield ctx.call_activity(split_into_scenes, input={"campaign_id": input["campaign_id"], "episode_id": input["episode_id"], "is_one_shot": input["is_one_shot"]})
            logging.info(f"✅ Step 1 Complete. Split into {len(scenes)} scenes")

            # Step 2: Summarize scenes
            logging.info("📝 Step 2: Starting scene summarization...")
            scenes_summaries = yield ctx.call_activity(
                summarize_scenes,
                input={
                    "scenes": scenes,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"],
                    "is_one_shot": input["is_one_shot"]
                }
            )
            logging.info(
                f"✅ Step 2 Complete. Generated {len(scenes_summaries)} scene summaries")

            # Step 3: Publish scenes to LightRAG
            logging.info("🚀 Step 3: Publishing scenes to LightRAG...")
            yield ctx.call_activity(
                publish_scenes_to_lightrag,
                input={
                    "scenes_summaries": scenes_summaries,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"]
                }
            )
            logging.info("✅ Step 3 Complete. Scenes published to LightRAG")

            # Step 4: Summarize episode
            logging.info("📖 Step 4: Starting episode summarization...")
            episode_summary = yield ctx.call_activity(
                summarize_episode,
                input={
                    "scenes_summaries": scenes_summaries,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"],
                    "is_one_shot": input["is_one_shot"]
                }
            )
            logging.info("✅ Step 4 Complete. Episode summary generated")

            # Step 5: Perform campaign summarization for series episodes (not one-shots)
            if not input["is_one_shot"]:
                logging.info("� Step 5: Starting campaign summarization...")
                yield ctx.call_activity(
                    summarize_campaign,
                    input={
                        "episode_summary": episode_summary,
                        "campaign_id": input["campaign_id"],
                        "episode_id": input["episode_id"],
                        "is_one_shot": input["is_one_shot"]
                    }
                )
                logging.info("✅ Step 5 Complete. Campaign summary generated")
            else:
                logging.info(
                    "⏩ Step 5: Skipping campaign summarization (one-shot episode)")

            # Step 6: Send notification for all episodes
            logging.info("📬 Step 6: Sending summary available notification...")
            yield ctx.call_activity(
                notify_summary_available,
                input={
                    "episode_summary": episode_summary,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"],
                    "is_one_shot": input["is_one_shot"]
                }
            )
            logging.info(
                "✅ Step 6 Complete. Summary available notification sent")

            logging.info("🎉 Workflow completed successfully!")
            return episode_summary
