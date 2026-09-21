from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.tools.trading_tools import build_tools

from ..helpers.utils import local_embedder, local_llm_deep

USE_MEMORY = False  # Set to False to disable memory and test if the issue is memory-related

@CrewBase
class AnalysisCrew:

    llm = local_llm_deep

    agents_config = "config/analysis_agents.yaml"  # relative to project root or absolute
    tasks_config = "config/analysis_tasks.yaml"

    tool_names = (
        "get_yfinance_data",
        "get_technical_indicators",
        "get_fundamental_analysis",
        "get_social_media_sentiment",
        "get_finnhub_news",
    )

    @agent
    def swing_trade_analyst(self) -> Agent:
        # Fresh tool objects per crew instance, and main.py builds one AnalysisCrew per
        # symbol, so max_usage_count=1 means once per symbol rather than once per process.
        return Agent(config=self.agents_config['swing_trade_analyst'],
                     tools=build_tools(*self.tool_names),
                     llm=self.llm,
                     memory=USE_MEMORY)

    @task
    def swing_analysis_task(self) -> Task:
        return Task(config=self.tasks_config['swing_analysis_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=USE_MEMORY, # Shared whiteboard for this crew
            embedder=local_embedder,
            share_crew=False,
            verbose=True
        )