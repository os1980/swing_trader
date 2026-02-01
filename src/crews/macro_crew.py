from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from helpers.utils import local_llm_deep, local_embedder
from src.tools.trading_tools import TOOLS


@CrewBase
class MacroCrew():

    llm = local_llm_deep
    agents_config = "config/macro_agents.yaml"  # relative to project root or absolute
    tasks_config = "config/macro_tasks.yaml"

    agent_tools = [TOOLS["get_macroeconomic_news"]]

    @agent
    def macro_strategist(self) -> Agent:
        return Agent(config=self.agents_config['macro_strategist'], tools=self.agent_tools,
                     llm=self.llm, memory=True)

    @task
    def macro_task(self) -> Task:
        return Task(config=self.tasks_config['macro_task'])

    @crew
    def crew(self) -> Crew:
        # Generate a unique path for THIS symbol to ensure zero overlap
        # symbol_storage_path = os.path.join(os.getcwd(), "memories", "tickers", self.symbol)
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=True, # Shared whiteboard for this crew
            embedder=local_embedder,
            share_crew=False,
            verbose=True
            # MANUALLY override the internal storages with the correct provider
            # This prevents the 'search' error you saw in the traceback
            # short_term_memory=ShortTermMemory(
            #     storage=RAGStorage(
            #         type="short_term",
            #         embedder_config=local_embedder,
            #         path=os.path.join(symbol_storage_path, "short_term")
            #     )
            # ),
            # entity_memory=EntityMemory(
            #     storage=RAGStorage(
            #         type="entities",
            #         embedder_config=local_embedder,
            #         path=os.path.join(symbol_storage_path, "entities")
            #     )
            # )
        )
