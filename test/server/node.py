import asyncio
import websockets
import json

async def handle_client(websocket):
    """Handle incoming WebSocket connections"""
    print(f"Client connected from {websocket.remote_address}")
    
    try:
        async for message in websocket:
            print(f"Received: {message}")
            
            # Echo back a response
            response = {
                "status": "received",
                "echo": message
            }
            await websocket.send(json.dumps(response))
            
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected from {websocket.remote_address}")

async def main():
    """Start the WebSocket server"""
    async with websockets.serve(handle_client, "localhost", 6767):
        print("WebSocket server started on ws://localhost:6767/ws")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())