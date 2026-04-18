
from pathlib import Path
from typing import Any, Dict

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.model.agent import get_llm
from app.log import get_logger

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"

class Application:
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.agents: Dict[str, Any] = {}

    def _load_prompt(self, filename: str) -> str:
        path = PROMPT_DIR / filename
        return path.read_text(encoding="utf-8").strip()

    def load_models(self) -> None:
        """Khởi tạo các embedding model để vector hóa chunk dữ liệu lưu vào vector DB."""
        logger.info("Loading embedding models...")
        # TODO: khởi tạo embedding model ở đây, ví dụ:
        # from langchain_community.embeddings import HuggingFaceEmbeddings
        # self.models["embedder"] = HuggingFaceEmbeddings(model_name="...")
        logger.info("Embedding models loaded")

    async def load_agent(self, tools: list = None) -> None:
        """Khởi tạo LangChain agent với LLM và danh sách tools tùy chọn."""
        tools = tools or []
        llm = get_llm(stream=False)
        system_prompt = self._load_prompt("chat_prompt.md")
        logger.info("Loaded system prompt from app/prompt/chat_prompt.md")

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

        self.agents["chat_agent"] = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
        )
        logger.info(f"Agent 'chat_agent' loaded | tools={[t.name for t in tools]}")

    def get_model(self, name_model: str) -> Any:
        return self.models[name_model]

    def get_agent(self, name_agent: str) -> Any:
        return self.agents[name_agent]

    def cleanup_model(self) -> None:
        self.models.clear()
        logger.info("Embedding models cleared")

application = Application()