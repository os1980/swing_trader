from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from helpers.utils import local_llm_deep, local_embedder
from helpers.trade_signals import TradeSignal

@CrewBase
class StrategyCrew():

    llm = local_llm_deep

    agents_config = "config/strategy_agents.yaml"  # relative to project root or absolute
    tasks_config = "config/strategy_tasks.yaml"

    @agent
    def strategy_manager(self) -> Agent:
        return Agent(config=self.agents_config['strategy_manager'], llm=self.llm, memory=True)

    @task
    def strategy_task(self) -> Task:
        return Task(config=self.tasks_config['strategy_task'],
                    output_json=TradeSignal,)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=True, # Shared whiteboard for this crew
            embedder=local_embedder,
            share_crew=False,
        )