# TTRPG summarizer

This project is a FastAPI + Dapr Workflows service that turns tabletop RPG recordings into structured summaries. It transcribes audio and process the transcription to provide a summary of what happened during the episode or campaign

## Features

- Pluggable speech-to-text (Supported backend: Azure OpenAI or local Whisper)
- Detailed summarization using Semantic Kernel (Supported backend: Azure OpenAI)
- FastAPI HTTP API to kick off workflows
- Configurable data source and destination using Dapr bindings
- OpenTelemetry traces, logs, and metrics (OTLP/gRPC)

## Usage

The purpose of this project is to provide a seamless way to generate structured summaries from tabletop RPG recordings. This project uses [Dapr](https://github.com/dapr/dapr).

### Sample output
```json
{
  "session_overview": "The party investigates mysterious disappearances in the village of Millhaven, uncovering a cult of shadow worshippers operating from beneath the old mill. After infiltrating their lair and confronting the cult leader, they rescue the missing villagers and discover ancient artifacts tied to a larger conspiracy threatening the realm.",
  "key_events": [
    "Party arrives in Millhaven and learns about the missing villagers from Mayor Aldric",
    "Investigation at the old mill reveals hidden entrance to underground chambers",
    "Encounter with shadow cultists and their summoned creatures",
    "Discovery of ritual chamber with imprisoned villagers",
    "Confrontation with Cultist Leader Malachar and disruption of the shadow ritual",
    "Rescue of villagers and seizure of the Shadow Crystal artifact",
    "Village celebration and revelation of larger threat from the Order of the Void"
  ],
  "character_updates": [
    {
      "name": "Thorin Ironbeard",
      "changes": [
        "Gained experience in detecting undead creatures",
        "Formed strong bond with rescued villager child, Tommy",
        "Acquired minor curse from Shadow Crystal exposure (temporary strength reduction)"
      ]
    },
    {
      "name": "Lyra Moonwhisper",
      "changes": [
        "Successfully identified and dispelled shadow magic wards",
        "Learned new spell: Detect Evil and Good from studying cult texts",
        "Established contact with local nature spirits who aided the investigation"
      ]
    },
    {
      "name": "Garrett the Swift",
      "changes": [
        "Demonstrated exceptional stealth skills infiltrating the cult lair",
        "Suffered moderate injuries from shadow creature claws (healing required)",
        "Discovered hidden talent for reading ancient runic inscriptions"
      ]
    }
  ],
  "npc_updates": [
    {
      "name": "Mayor Aldric Stoneheart",
      "details": [
        "Revealed knowledge of ancient mill's dark history",
        "Offered party permanent residence in Millhaven as reward",
        "Requested party's aid in fortifying village defenses"
      ]
    },
    {
      "name": "Malachar the Shadow Binder",
      "details": [
        "Cult leader seeking to summon avatar of shadow deity",
        "Escaped through shadow portal after ritual disruption",
        "Left behind journal revealing Order of the Void connections",
        "Holds personal vendetta against Lyra's mentor, Archdruid Elara"
      ]
    },
    {
      "name": "Tommy Fletcher",
      "details": [
        "Young villager rescued from cult sacrifice",
        "Witnessed cult's planning meetings while imprisoned",
        "Possesses natural resistance to shadow magic",
        "Became honorary member of the party"
      ]
    }
  ],
  "items_and_clues": [
    {
      "name": "Shadow Crystal",
      "description": "Dark crystalline artifact used to focus shadow magic rituals",
      "significance": "Key component for summoning shadow entities; multiple crystals exist across the realm"
    },
    {
      "name": "Malachar's Journal",
      "description": "Leather-bound tome containing cult plans and Order of the Void intelligence",
      "significance": "Reveals locations of other cult cells and upcoming convergence ritual"
    },
    {
      "name": "Ancient Mill Blueprints",
      "description": "Original architectural plans showing hidden chambers and passages",
      "significance": "Indicates mill was purposely built over ancient shadow temple site"
    },
    {
      "name": "Rune-carved Daggers",
      "description": "Set of three ceremonial daggers with shadow magic inscriptions",
      "significance": "Required implements for shadow summoning rituals; one still missing"
    },
    {
      "name": "Villager Testimonies",
      "description": "Accounts from rescued villagers about cult recruitment methods",
      "significance": "Reveals cult has infiltrated other nearby settlements"
    }
  ],
  "open_threads": [
    {
      "description": "Malachar escaped and threatens revenge against the party, particularly Lyra",
      "priority": "high",
      "related_characters": ["Malachar", "Lyra Moonwhisper"]
    },
    {
      "description": "The Order of the Void plans a major convergence ritual in three months",
      "priority": "high", 
      "related_characters": ["Order of the Void", "Party"]
    },
    {
      "description": "Third ceremonial dagger remains unaccounted for and is needed for cult rituals",
      "priority": "medium",
      "related_characters": ["Party", "Order of the Void"]
    },
    {
      "description": "Tommy's natural shadow magic resistance may be key to stopping the Order",
      "priority": "medium",
      "related_characters": ["Tommy Fletcher", "Party"]
    },
    {
      "description": "Connection between Malachar and Archdruid Elara's past needs investigation",
      "priority": "medium",
      "related_characters": ["Malachar", "Lyra Moonwhisper", "Archdruid Elara"]
    },
    {
      "description": "Other villages mentioned in cult documents require warning and protection",
      "priority": "low",
      "related_characters": ["Party", "Village leaders"]
    }
  ],
  "continuity_notes": [
    "Thorin's curse will require magical healing or will fade naturally in 1-2 sessions",
    "Garrett's injuries need proper medical attention before next adventure",
    "Tommy should be integrated as recurring NPC who provides local knowledge",
    "Shadow Crystal's influence may affect party members who carried it for extended periods",
    "Mayor Aldric expects regular updates on Order of the Void threat",
    "Nature spirits contacted by Lyra may provide ongoing intelligence about shadow magic activity",
    "Party reputation in Millhaven grants advantage on social interactions with villagers"
  ]
}
```
## Configuration

### Environment Variables

This project uses the following environment variables:


| env variable                                                        | description                                                                                                                                                                                      | required | default               |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | --------------------- |
| HUGGING_FACE_TOKEN                                                  | Hugging Face API token. Required to use some models. **You must accept some models terms and conditions, see [here](https://github.com/m-bain/whisperX?tab=readme-ov-file#speaker-diarization)** | true     |                       |
| AI_FOUNDRY_PROJECT_ENDPOINT                                         | Azure AI Foundry project endpoint                                                                                                                                                                | true     |                       |
| AZURE_CHAT_DEPLOYMENT_NAME                                          | Azure Model to use for chat completion                                                                                                                                                           | true     |                       |
| AZURE_AUDIO_DEPLOYMENT_NAME                                         | Azure Model to use for speech to text                                                                                                                                                            | false    |                       |
| DAPR_AUDIO_STORE_NAME                                               | Dapr binding name for audio store                                                                                                                                                                | false    | audio-store           |
| DAPR_SUMMARY_STORE_NAME                                             | Dapr binding name for summary store                                                                                                                                                              | false    | summary-store         |
| OTLP_ENDPOINT                                                       | OpenTelemetry Protocol (OTLP) endpoint                                                                                                                                                           | false    | http://localhost:4317 |
| SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS_SENSITIVE | Enable sensitive diagnostics data collection                                                                                                                                                     | false    | false                 |
| INFERENCE_DEVICE                                                    | Device for ML inference (cpu, cuda)                                                                                                                                                              | false    | cpu                   |
| HTTP_HOST                                                           | HTTP server host                                                                                                                                                                                 | false    | 0.0.0.0               |
| HTTP_PORT                                                           | HTTP server port                                                                                                                                                                                 | false    | 8000                  |
| AZURE_TENANT_ID                                                     | [Azure subscription id](https://learn.microsoft.com/fr-fr/dotnet/api/azure.identity.environmentcredential?view=azure-dotnet)                                                                     | false    | 8000                  |
| AZURE_CLIENT_ID                                                     | [Azure spn id](https://learn.microsoft.com/fr-fr/dotnet/api/azure.identity.environmentcredential?view=azure-dotnet)                                                                              | false    | 8000                  |
| AZURE_CLIENT_SECRET                                                 | [Azure spn secret](https://learn.microsoft.com/fr-fr/dotnet/api/azure.identity.environmentcredential?view=azure-dotnet)                                                                          | false    | 8000                  |

## Data flow  

```mermaid
graph LR

    %% Audio-to-Summary Workflow
    G[Audio-to-Summary Workflow]
    G --> I2{Step 1: Transcription.  Backend ?}
    I2 -->|Azure OpenAI| I3[Azure Whisper API]
    I2 -->|Local| I4[Local WhisperX Model]
    I3 --> I5[Generate Transcript with Diarization]
    I4 --> I5

    I5 --> J[Step 2: Split into Scenes]
    
    %% Transcript-to-Summary Workflow (joins here)
    H[Transcript-to-Summary Workflow]
    H --> K[Load Existing Transcript]
    K --> J
    
    J --> L[Step 3: Summarize Scenes]
    L --> L2[Azure OpenAI Chat Model]
    
    L2 --> M[Step 4: Summarize Episode / Campaign]
    
    %% Styling
    classDef workflow fill:#e1f5fe
    classDef storage fill:#f3e5f5
    classDef ai fill:#e8f5e8
    classDef api fill:#fff3e0
    
    class G,H workflow
    class B,D,Q,S storage
    class I3,I4,L2,M2,O3 ai
    class E,F api
```


