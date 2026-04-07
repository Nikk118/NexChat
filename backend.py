from langchain_huggingface import HuggingFaceEndpoint,ChatHuggingFace
from dotenv import load_dotenv
from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Literal,Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage,HumanMessage
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    temperature=0.7,
    max_new_tokens=512
)

llm=ChatHuggingFace(
    llm=llm
)

class chatState(TypedDict):
    messages:Annotated[list[BaseMessage],add_messages]

def chat_node(state:chatState)->chatState:
    messages=state["messages"]
    response=llm.invoke(messages)
    return {'messages':[response]}

graph=StateGraph(chatState)

checkpoint=MemorySaver()

graph.add_node("chat_node",chat_node)
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

chatbot=graph.compile(checkpointer=checkpoint)

