from crewai import LLM
import pathlib
import os


CONFIG_BASE_DIR = str(pathlib.Path(__file__).parent / "config")
# MEMORY_BASE_DIR = pathlib.Path(__file__).parent.parent / "knowledge"
#
# # Force the storage directory to be local before any crews are initialized
#
# os.environ["MEMORY_BASE_DIR"] = str(MEMORY_BASE_DIR)
# os.environ["CREWAI_STORAGE_DIR"] = str(MEMORY_BASE_DIR)
#
#
# # Ensure the directory exists
# MEMORY_BASE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG = {
    "results_dir": "./results",
    "llm_provider": "ollama",
    "deep_think_llm": "llama3:8b", #"deepseek-r1:8b",  # Local model
    "quick_think_llm": "llama3:8b",  #"gemma3:4b",  # Same for simplicity
    "ollama_base_url": "http://localhost:11434",
    "max_debate_rounds": 2,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "llm_temperature": 0.0,
    "online_tools": True,
    "swing_evaluation_days": 21,  # For ground_truth (swing trading horizon)
}


local_llm_deep = LLM(
        api_key=os.getenv("OPENAI_API_KEY", "FAKE"),
        model=f"""{CONFIG["llm_provider"]}/{CONFIG["deep_think_llm"]}""",
        base_url=CONFIG["ollama_base_url"],
        temperature=CONFIG["llm_temperature"],
        max_debate_rounds=CONFIG["max_debate_rounds"],
        max_risk_discuss_rounds=CONFIG["max_risk_discuss_rounds"],
        max_recur_limit=CONFIG["max_recur_limit"],
    )



local_embedder = {
    "provider": "ollama",
    "config": {
        "model_name": "nomic-embed-text",
        "base_url": CONFIG["ollama_base_url"],
        "api_key": ""
    }
}


#
# local_llm_quick = LLM(
#         api_key=CONFIG.get("llm_api_key", "dummy"),
#         model=f"""{CONFIG["llm_provider"]}/{CONFIG["quick_think_llm"]}""",
#         base_url=CONFIG["ollama_base_url"],
#         emperature=CONFIG["llm_temperature"],
#         max_debate_rounds=CONFIG["max_debate_rounds"],
#         max_risk_discuss_rounds=CONFIG["max_risk_discuss_rounds"],
#         max_recur_limit=CONFIG["max_recur_limit"],
#     )