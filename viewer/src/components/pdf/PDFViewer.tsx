"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Worker, Viewer } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/default-layout/lib/styles/index.css";

import ChatPane from "../chat/ChatPane"; 
import ResizablePanel from "../common/ResizablePanel";
import MathJaxProvider from "../providers/MathJaxProvider";
import RuminateButton from "../viewer/RuminateButton";
import ObjectiveSelector from "../viewer/ObjectiveSelector";
import { useRumination } from "../../hooks/useRumination";

export interface Block {
  id: string;
  type: string;
  block_type: string;
  html_content: string;
  polygon: number[][];
  page_number?: number;
  pageIndex?: number;
  children?: Block[];
  images?: { [key: string]: string };
}

// A minimal Block Info component (for the built-in sidebar tab, if you still want it)
function BlockInformation({ block }: { block: Block | null }) {
  if (!block) {
    return (
      <div className="p-4 text-gray-500">
        Select a block to view its information
      </div>
    );
  }
  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="font-semibold mb-2">Basic Information</h3>
        <div className="space-y-1">
          <p>
            <span className="font-medium">ID:</span> {block.id}
          </p>
          <p>
            <span className="font-medium">Type:</span> {block.block_type}
          </p>
          {/* <p>
            <span className="font-medium">Content:</span>
          </p> */}
          {/* <div
            className="mt-1 p-2 bg-gray-50 rounded text-sm"
            dangerouslySetInnerHTML={{ __html: block.html }}
          /> */}
        </div>
      </div>
    </div>
  );
}

// Add utility function for hash calculation
async function calculateHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// Add a type for our cache structure
interface CachedDocument {
  documentId: string;
  blockConversations: {[blockId: string]: string};
}

export default function PDFViewer() {
  const [pdfFile, setPdfFile] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Flattened blocks array
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [selectedBlock, setSelectedBlock] = useState<Block | null>(null);
  // Track active conversations
  const [blockConversations, setBlockConversations] = useState<{[blockId: string]: string}>({});

  const fileInputRef = useRef<HTMLInputElement>(null);

  const { startRumination, isRuminating, error: ruminationError, status, currentBlockId } = useRumination({ 
    documentId: documentId || '',
    onBlockProcessing: (blockId) => {
      if (blockId) {
        // Find the block in our blocks array
        const block = blocks.find(b => b.id === blockId);
        if (block) {
          setSelectedBlock(block);
        }
      } else {
        // Clear selection when rumination is complete or on error
        setSelectedBlock(null);
      }
    }
  });

  const [currentObjective, setCurrentObjective] = useState("Focus on key vocabulary and jargon that a novice reader would not be familiar with.");

  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    toolbarPlugin: {
      fullScreenPlugin: {
        onEnterFullScreen: () => {},
        onExitFullScreen: () => {},
      },
      searchPlugin: {
        keyword: [''],
      },
    },

    // {/* <Print /> */}
    // {/* <ShowProperties /> */}
    // {/* <Download /> */}
    // {/* <EnterFullScreen /> */}

    renderToolbar: (Toolbar) => (
      <Toolbar>
        {(slots) => {
          const {
            CurrentPageInput,
            GoToNextPage,
            GoToPreviousPage,
            NumberOfPages,
            ShowSearchPopover,
            SwitchTheme,
            Zoom,
            ZoomIn,
            ZoomOut,
          } = slots;
          return (
            <div className="flex items-center justify-between w-full px-4">
              {/* Page Navigation Group */}
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <CurrentPageInput />
                  <span className="text-neutral-600">/</span>
                  <span className="text-neutral-600">
                    <NumberOfPages />
                  </span>
                </div>
                <GoToPreviousPage />
                <GoToNextPage />
              </div>

              {/* Ruminate Button */}
              {documentId && (
                <div className="flex items-center gap-2">
                  <RuminateButton
                    isRuminating={isRuminating}
                    error={ruminationError}
                    status={status}
                    onRuminate={() => startRumination(currentObjective)}
                  />
                  <span className="text-neutral-600">on</span>
                  <ObjectiveSelector onObjectiveChange={setCurrentObjective} />
                </div>
              )}

              {/* Zoom Controls Group */}
              <div className="flex items-center gap-2">
                <ZoomOut />
                <Zoom />
                <ZoomIn />
              </div>

              {/* Utilities Group */}
              <div className="flex items-center gap-2 ml-4">
                <ShowSearchPopover />
                <SwitchTheme />
              </div>
            </div>
          );
        }}
      </Toolbar>
    ),
    sidebarTabs: (defaultTabs) => [
      {
        content: <BlockInformation block={selectedBlock} />,
        icon: (
          <svg viewBox="0 0 24 24" width="24px" height="24px">
            <path
              d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"
              fill="currentColor"
            />
          </svg>
        ),
        title: "Block Information",
      },
    ],
  });

  // Add page layout customization
  const pageLayout = {
    buildPageStyles: () => ({
      boxShadow: '0 0 4px rgba(0, 0, 0, 0.15)',
      margin: '16px auto',
      borderRadius: '4px',
    }),
    transformSize: ({ size }: { size: { width: number; height: number } }) => ({
      height: size.height,
      width: size.width,
    }),
  };

  // Example flattening function
  const parseBlock = (block: Block, nextPageIndex: number, all: Block[]): number => {
    if (block.block_type === "Page") {
      if (typeof block.page_number === "number") {
        block.pageIndex = block.page_number - 1;
        if (block.pageIndex >= nextPageIndex) {
          nextPageIndex = block.pageIndex + 1;
        }
      } else {
        block.pageIndex = nextPageIndex;
        nextPageIndex++;
      }
    } else {
      if (typeof block.pageIndex !== "number") {
        block.pageIndex = 0;
      }
    }
    all.push(block);
    if (block.children) {
      for (const child of block.children) {
        child.pageIndex = block.pageIndex;
        nextPageIndex = parseBlock(child, nextPageIndex, all);
      }
    }
    return nextPageIndex;
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    try {
      // Calculate file hash
      const fileHash = await calculateHash(file);
      
      // Check localStorage for existing document data
      const cachedDocuments = JSON.parse(localStorage.getItem('pdfDocuments') || '{}') as {[hash: string]: CachedDocument};
      const cachedData = cachedDocuments[fileHash];
      
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
      
      if (cachedData) {
        // Try to fetch the existing document
        try {
          const docResponse = await fetch(`${apiUrl}/documents/${cachedData.documentId}`);
          if (docResponse.ok) {
            const docData = await docResponse.json();
            if (docData.status === "READY") {
              // Cached document exists and is ready
              setDocumentId(cachedData.documentId);
              // Restore cached conversations
              setBlockConversations(cachedData.blockConversations || {});
              
              const blocksResp = await fetch(`${apiUrl}/documents/${cachedData.documentId}/blocks`);
              const blocksData = await blocksResp.json();
              if (Array.isArray(blocksData)) {
                setBlocks(blocksData);
              }
              
              // Set PDF file for viewing
              const reader = new FileReader();
              reader.onload = (e) => {
                setPdfFile(e.target?.result as string);
              };
              reader.readAsDataURL(file);
              setLoading(false);
              return;
            }
          }
        } catch (error) {
          console.log('Cached document not found, processing as new upload');
        }
      }
      
      // If we get here, either no cached document or it wasn't valid
      // Process as new upload
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target?.result as string;
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${apiUrl}/documents/`, {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        const docId = data.id;
        setDocumentId(docId);
        
        // Reset conversations for new document
        setBlockConversations({});

        // Store the new document data in localStorage
        cachedDocuments[fileHash] = {
          documentId: docId,
          blockConversations: {}  // Start with empty conversations
        };
        localStorage.setItem('pdfDocuments', JSON.stringify(cachedDocuments));

        // Poll until document status becomes "READY"
        let status = data.status;
        while (status !== "READY") {
          const statusResp = await fetch(`${apiUrl}/documents/${docId}`);
          const docData = await statusResp.json();
          status = docData.status;
          await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Fetch document blocks once the document is ready
        const blocksResp = await fetch(`${apiUrl}/documents/${docId}/blocks`);
        const blocksData = await blocksResp.json();
        if (Array.isArray(blocksData)) {
          setBlocks(blocksData);
        }

        setPdfFile(base64);
      };
      reader.readAsDataURL(file);
    } catch (error) {
      console.error("Error processing PDF:", error);
    }
    setLoading(false);
  };

  // Update cache when conversations change
  useEffect(() => {
    if (documentId) {
      const cachedDocuments = JSON.parse(localStorage.getItem('pdfDocuments') || '{}') as {[hash: string]: CachedDocument};
      // Find the hash for this document
      const hash = Object.keys(cachedDocuments).find(
        key => cachedDocuments[key].documentId === documentId
      );
      if (hash) {
        cachedDocuments[hash] = {
          documentId,
          blockConversations
        };
        localStorage.setItem('pdfDocuments', JSON.stringify(cachedDocuments));
      }
    }
  }, [blockConversations, documentId]);

  const handleBlockClick = useCallback((block: Block) => {
    console.log('Selected Block:', {
      id: block.id,
      type: block.block_type,
      content: block.html_content,
      fullBlock: block
    });
    setSelectedBlock(block);
  }, []);

  const renderOverlay = useCallback(
    (props: { pageIndex: number; scale: number; rotation: number }) => {
      const { scale, pageIndex } = props;
      
      // Add this debug log to see page number distribution
      const pageNumberDistribution = blocks.reduce((acc, b) => {
        const pageNum = b.page_number ?? 'undefined';
        acc[pageNum] = (acc[pageNum] || 0) + 1;
        return acc;
      }, {} as Record<string | number, number>);
      
      const filteredBlocks = blocks.filter(
        (b) => b.block_type !== "Page" && (b.page_number ?? 0) === pageIndex
      );
      
      return (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
          }}
        >
          {filteredBlocks.map((b) => {
            if (!b.polygon || b.polygon.length < 4) return null;
            const x = Math.min(...b.polygon.map((p) => p[0]));
            const y = Math.min(...b.polygon.map((p) => p[1]));
            const w = Math.max(...b.polygon.map((p) => p[0])) - x;
            const h = Math.max(...b.polygon.map((p) => p[1])) - y;

            const isSelected = selectedBlock?.id === b.id;
            const style = {
              position: "absolute" as const,
              left: `${x * scale}px`,
              top: `${y * scale}px`,
              width: `${w * scale}px`,
              height: `${h * scale}px`,
              backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
              border: isSelected
                ? '2px solid rgba(59, 130, 246, 0.8)'
                : '1px solid rgba(59, 130, 246, 0.3)',
              cursor: 'pointer',
              transition: 'all 0.2s ease-in-out',
              zIndex: isSelected ? 2 : 1,
              borderRadius: '2px',
            };
            return (
              <div
                key={b.id}
                style={style}
                className="hover:bg-primary-100/10 hover:border-primary-400 hover:shadow-block-hover"
                onClick={() => handleBlockClick(b)}
                title={b.html_content?.replace(/<[^>]*>/g, "") || ""}
              />
            );
          })}
        </div>
      );
    },
    [blocks, selectedBlock, handleBlockClick]
  );

  // Update the array name and contents to include Picture blocks
  const chatEnabledBlockTypes = [
    "text",
    "sectionheader",
    "pageheader",
    "pagefooter",
    "listitem",
    "footnote",
    "reference",
    "picture",
    "textinlinemath",
    "equation",
    "table"
  ].map(type => type.toLowerCase());

  // Update the condition name to match
  const isChatEnabled = selectedBlock?.block_type && 
    chatEnabledBlockTypes.includes(selectedBlock.block_type.toLowerCase());

  // Add state for chat pane width
  const [chatPaneWidth, setChatPaneWidth] = useState(384);

  return (
    <MathJaxProvider>
      <div className="h-screen grid overflow-hidden" style={{ 
        gridTemplateColumns: selectedBlock && isChatEnabled ? `1fr ${chatPaneWidth}px` : '1fr' 
      }}>
        {/* Left side: PDF viewer - add overflow-hidden */}
        <div className="relative bg-white shadow-lg overflow-hidden">
          {!pdfFile ? (
            <div className="flex h-full items-center justify-center bg-neutral-100">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
                ref={fileInputRef}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg
                       shadow-md hover:bg-primary-700 
                       transition-colors duration-200
                       flex items-center space-x-2"
                disabled={loading}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>{loading ? "Processing..." : "Upload PDF"}</span>
              </button>
            </div>
          ) : (
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
              <div 
                style={{
                  border: 'none',
                  height: '100%',
                  backgroundColor: 'rgb(243 244 246)',
                }}
                className="overflow-auto"
              >
                <Viewer
                  fileUrl={pdfFile}
                  plugins={[defaultLayoutPluginInstance]}
                  defaultScale={1.2}
                  theme="light"
                  pageLayout={pageLayout}
                  renderLoader={(percentages: number) => (
                    <div className="flex items-center justify-center p-4">
                      <div className="w-full max-w-sm">
                        <div className="bg-white p-4 rounded-lg shadow-sm">
                          <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-primary-600 transition-all duration-300"
                              style={{ width: `${Math.round(percentages)}%` }}
                            />
                          </div>
                          <div className="text-sm text-neutral-600 mt-2 text-center">
                            Loading {Math.round(percentages)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  renderPage={(props) => (
                    <>
                      {props.canvasLayer.children}
                      {props.textLayer.children}
                      {renderOverlay(props)}
                    </>
                  )}
                />
              </div>
            </Worker>
          )}
        </div>

        {/* Right side: Chat pane */}
        {selectedBlock && isChatEnabled && (
          <ResizablePanel 
            width={chatPaneWidth}
            onResize={setChatPaneWidth}
          >
            <ChatPane
              key={selectedBlock.id}
              block={selectedBlock}
              documentId={documentId!}
              conversationId={blockConversations[selectedBlock.id]}
              onConversationCreated={(convId) => {
                setBlockConversations(prev => ({
                  ...prev,
                  [selectedBlock.id]: convId
                }));
              }}
              onClose={() => setSelectedBlock(null)}
            />
          </ResizablePanel>
        )}
      </div>
    </MathJaxProvider>
  );
}
