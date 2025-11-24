from langgraph.graph import StateGraph

class LangGraphAgent:
    def __init__(self, llm_service, rag_service):
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build LangGraph workflow for conversation orchestration"""
        
        def retrieve_context(state):
            """Node: Retrieve relevant conversation context"""
            user_id = state["user_id"]
            message = state["message"]
            
            # Get conversation history and relevant context
            context = self.rag_service.get_conversation_context(user_id, message)
            state["context"] = context
            return state
        
        def generate_response(state):
            """Node: Generate LLM response with context"""
            context = state["context"]
            message = state["message"]
            
            prompt = f"""
            Previous Conversation Context:
            {context}
            
            Current User Message: {message}
            
            You are a helpful AI assistant specializing in video editing. 
            If the user asks about video editing, focus on:
            - Subtitle customization (font, size, position)
            - Video trimming and silence removal
            - General video editing tips
            
            Provide clear, helpful responses.
            """
            
            response = self.llm_service.get_completion(prompt)
            state["response"] = response
            return state
        
        def store_conversation(state):
            """Node: Store conversation in RAG system"""
            self.rag_service.store_conversation(
                state["user_id"], 
                state["message"], 
                state["response"]
            )
            return state
        
        # Build the graph using StateGraph
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("retrieve", retrieve_context)
        workflow.add_node("generate", generate_response)
        workflow.add_node("store", store_conversation)
        
        # Define edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "store")
        workflow.add_edge("store", "__end__")
        
        return workflow.compile()
    
    async def process_message(self, user_id: str, message: str) -> str:
        """Process message through LangGraph workflow"""
        try:
            initial_state = {
                "user_id": user_id,
                "message": message,
                "context": "",
                "response": ""
            }
            
            # Execute the graph
            final_state = self.graph.invoke(initial_state)
            return final_state["response"]
            
        except Exception as e:
            return f" I apologize, but I encountered an error: {str(e)}"