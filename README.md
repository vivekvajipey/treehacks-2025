# Ruminate - AI Reading Companion

An intelligent AI reading companion that helps you understand complex documents in real-time. Upload any PDF and watch as our AI analyzes and explains content block-by-block, adapting to your learning objectives.

![Ruminate Demo](./docs/demo.gif)

## Features 🚀

- **Adaptive AI Analysis**: Process documents with customizable learning objectives
- **Real-Time Processing**: Watch as the AI analyzes content block-by-block
- **Interactive Annotations**: Click on highlighted text for detailed explanations
- **Context-Aware Chat**: Discuss specific sections with AI that maintains document context
- **Technical Content Support**: Handles LaTeX equations, tables, and figures
- **Progress Visualization**: Visual feedback during document processing
- **Conversation Memory**: Maintains context across document sections

## Tech Stack 💻

### Frontend
- **Framework**: Next.js 13 (App Router)
- **UI Components**: React with TypeScript
- **PDF Processing**: react-pdf-viewer
- **Animations**: Framer Motion
- **Styling**: Tailwind CSS
- **State Management**: React Hooks + Context

### Backend
- **API**: FastAPI
- **Database**: SQLite with SQLAlchemy
- **Document Processing**: DataLab Marker API, Gemini API
- **AI Integration**: OpenAI API, Gemini API
- **Real-Time Updates**: Server-Sent Events (SSE)

## Project Structure 📁

```
root
├── viewer/                 # Frontend application
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   │   ├── blocks/    # Block-specific components
│   │   │   ├── chat/      # Chat interface
│   │   │   ├── pdf/       # PDF viewer components
│   │   │   └── viewer/    # Main viewer components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── services/      # API services
│   │   └── types/         # TypeScript definitions
│   └── public/            # Static assets
│
└── src/                   # Backend application
    ├── api/               # FastAPI routes
    ├── models/            # Data models
    ├── repositories/      # Data access layer
    ├── services/          # Business logic
    └── config/            # Configuration files
```

## Key Components 🔧

### Document Processing Pipeline

1. **Upload & Processing**
```typescript
// Document upload handling
const handleFileUpload = async (file: File) => {
  // Calculate document hash for caching
  const hash = await calculateHash(file);
  
  // Check cache or process new document
  const formData = new FormData();
  formData.append("file", file);
  
  // Upload to processing endpoint
  const response = await fetch(`${API_URL}/documents/`, {
    method: "POST",
    body: formData
  });
};
```

2. **Block Detection**
```python
# Backend block processing
class Block(BaseModel):
    id: str
    document_id: str
    block_type: BlockType
    html_content: str
    polygon: List[List[float]]
    page_number: Optional[int]
```

3. **Real-Time Processing**
```typescript
// Frontend rumination hook
const useRumination = ({ documentId, onBlockProcessing }) => {
  // Connect to SSE for real-time updates
  useEffect(() => {
    const eventSource = new EventSource(
      `${API_URL}/insights/ruminate/stream/${documentId}`
    );
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Handle real-time updates
    };
  }, [documentId]);
};
```

### AI Integration

1. **Structured Insight Generation**
```python
class StructuredInsightService:
    async def analyze_block(self, block: Block, objective: str) -> StructuredInsight:
        # Generate block insights with specific objective
        conversation_id = f"conv-{block.id}"
        messages = self._build_messages(block, objective)
        
        # Get AI response
        response = await self.llm_service.generate_response(messages)
        
        # Extract annotations
        annotations = await self._extract_annotations(block.html_content)
        
        return StructuredInsight(
            block_id=block.id,
            insight=response,
            annotations=annotations
        )
```

2. **Context Management**
```python
class ChatService:
    def __init__(self, conversation_repository, document_repository, llm_service):
        self.conversation_repository = conversation_repository
        self.document_repository = document_repository
        self.llm_service = llm_service
    
    async def process_message(self, conversation_id: str, content: str) -> Message:
        # Maintain conversation context
        history = await self.conversation_repository.get_history(conversation_id)
        response = await self.llm_service.generate_response(history + [content])
        return response
```

## Setup & Installation 🛠️

1. **Clone the repository**
```bash
git clone https://github.com/vivekvajipey/treehacks-2025.git
cd treehacks-2025
```

2. **Install dependencies**
```bash
# Frontend
cd viewer
npm install

# Backend
cd ../
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Environment Setup**
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Backend (.env)
OPENAI_API_KEY=your_key_here
DATALAB_API_KEY=your_key_here
```

4. **Run the application**
```bash
# Frontend
cd viewer
npm run dev

# Backend
cd ../
python -m src.main
```

## API Routes 🛣️

### Document Management
- `POST /documents/` - Upload new document
- `GET /documents/{id}` - Get document status
- `GET /documents/{id}/blocks` - Get document blocks

### Insights
- `POST /insights/ruminate` - Start rumination process
- `GET /insights/ruminate/stream/{document_id}` - Stream processing updates
- `GET /insights/block/{block_id}` - Get block insights

### Conversation
- `POST /conversation/{conversation_id}/messages` - Send message
- `GET /conversation/{conversation_id}/history` - Get chat history