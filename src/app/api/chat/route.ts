import ollama from 'ollama';

const model = "gemma3n:e4b"

export async function POST(request: Request) {
    try {
        const { messages } = await request.json();

        // Convert messages to ollama format
        const ollamaMessages = messages.map((msg: { role: string; content: string }) => ({
            role: msg.role,
            content: msg.content
        }));

        // Create a readable stream for Server-Sent Events
        const stream = new ReadableStream({
            async start(controller) {
                try {
                    const response = await ollama.chat({
                        model: process.env.AI_MODEL || model ,
                        messages: ollamaMessages,
                        stream: true,
                    });

                    let fullContent = '';
                    let insideThinkTags = false;
                    let bufferContent = '';

                    for await (const part of response) {
                        if (part.message?.content) {
                            bufferContent += part.message.content;
                            fullContent += part.message.content;
                            
                            // Process buffer character by character to detect think tags
                            let processedContent = '';
                            let i = 0;
                            
                            while (i < bufferContent.length) {
                                // Check for opening think tag
                                if (bufferContent.substring(i).startsWith('<think>')) {
                                    insideThinkTags = true;
                                    i += 7; // Skip '<think>'
                                    continue;
                                }
                                
                                // Check for closing think tag
                                if (bufferContent.substring(i).startsWith('</think>')) {
                                    insideThinkTags = false;
                                    i += 8; // Skip '</think>'
                                    continue;
                                }
                                
                                // If not inside think tags, add to processed content
                                if (!insideThinkTags) {
                                    processedContent += bufferContent[i];
                                }
                                
                                i++;
                            }
                            
                            // Only stream if we have processed content to send
                            if (processedContent) {
                                const data = JSON.stringify({
                                    role: 'bot',
                                    content: processedContent,
                                    fullContent: removeThinkTags(fullContent),
                                    done: part.done || false
                                });
                                
                                controller.enqueue(new TextEncoder().encode(`data: ${data}\n\n`));
                            }
                            
                            // Reset buffer, keeping any incomplete tag at the end
                            bufferContent = '';
                        }

                        if (part.done) {
                            controller.close();
                            break;
                        }
                    }
                } catch (error) {
                    console.error('Erreur avec Ollama:', error);
                    const errorData = JSON.stringify({
                        role: 'bot',
                        content: 'Désolé, une erreur s\'est produite lors de la communication avec l\'IA.',
                        error: true
                    });
                    controller.enqueue(new TextEncoder().encode(`data: ${errorData}\n\n`));
                    controller.close();
                }
            }
        });

        return new Response(stream, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        });
    } catch (error) {
        console.error('Erreur avec Ollama:', error);
        return Response.json(
            { 
                role: 'bot',
                content: 'Désolé, une erreur s\'est produite lors de la communication avec l\'IA.'
            },
            { status: 500 }
        );
    }
}

function removeThinkTags(text: string): string {
    return text.replace(/<think>[\s\S]*?<\/think>/g, '');
}