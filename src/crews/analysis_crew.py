from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from ..helpers.utils import local_llm_deep, local_embedder
from src.tools.trading_tools import TOOLS


@CrewBase
class AnalysisCrew():

    llm = local_llm_deep

    agents_config = "config/analysis_agents.yaml"  # relative to project root or absolute
    tasks_config = "config/analysis_tasks.yaml"

    tools = ['get_yfinance_data',
             'get_technical_indicators',
             'get_fundamental_analysis',
             'get_social_media_sentiment',
             'get_finnhub_news']
    agent_tools = []
    for tool in tools:
        agent_tools.append(TOOLS[tool])

    @agent
    def swing_trade_analyst(self) -> Agent:
        return Agent(config=self.agents_config['swing_trade_analyst'],
                     tools=self.agent_tools,
                     llm=self.llm,
                     memory=True)

    @task
    def swing_analysis_task(self) -> Task:
        return Task(config=self.tasks_config['swing_analysis_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=True, # Shared whiteboard for this crew
            embedder=local_embedder,
            share_crew=False,
            verbose=True
        )