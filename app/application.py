from pathlib import Path
from typing import Any, Dict

from app.model.llm import get_llm
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
        import torch
        from sentence_transformers import SentenceTransformer
        from FlagEmbedding import BGEM3FlagModel

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading embedding models on device={device}...")

        dense_model = SentenceTransformer(
            "AITeamVN/Vietnamese_Embedding_v2",
            device=device,
        )
        self.models["dense_embedder"] = dense_model
        logger.info("Loaded dense model: AITeamVN/Vietnamese_Embedding_v2")

        sparse_model = BGEM3FlagModel(
            "BAAI/bge-m3",
            use_fp16=True,
            device=device,
        )
        self.models["sparse_embedder"] = sparse_model
        logger.info("Loaded sparse model: BAAI/bge-m3")

        logger.info(f"All embedding models loaded | device={device}")

    # async def load_agent(self, tools: list = None) -> None:
    #     """Khởi tạo LangChain agent với LLM và danh sách tools tùy chọn."""
    #     tools = tools or []
    #     llm = get_llm(stream=False)
    #     system_prompt = self._load_prompt("chat_prompt.md")
    #     logger.info("Loaded system prompt from app/prompt/chat_prompt.md")

    #     prompt = ChatPromptTemplate.from_messages([
    #         ("system", system_prompt),
    #         MessagesPlaceholder("chat_history", optional=True),
    #         ("human", "{input}"),
    #         MessagesPlaceholder("agent_scratchpad"),
    #     ])

    #     agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    #     self.agents["chat_agent"] = AgentExecutor(
    #         agent=agent,
    #         tools=tools,
    #         verbose=True,
    #         max_iterations=5,
    #         handle_parsing_errors=True,
    #     )
    #     logger.info(f"Agent 'chat_agent' loaded | tools={[t.name for t in tools]}")

    def get_model(self, name_model: str) -> Any:
        return self.models[name_model]

    def get_agent(self, name_agent: str) -> Any:
        return self.agents[name_agent]

    def cleanup_model(self) -> None:
        self.models.clear()
        logger.info("Embedding models cleared")

application = Application()