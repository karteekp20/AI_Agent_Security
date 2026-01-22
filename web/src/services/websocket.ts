const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(orgId: string) {
    const wsUrl = `${WS_BASE_URL}/ws/${orgId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const { type, payload } = data;

      this.listeners.get(type)?.forEach(callback => callback(payload));
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect(orgId);
        }, 1000 * Math.pow(2, this.reconnectAttempts));
      }
    };
  }

  subscribe(eventType: string, callback: (data: any) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
    this.listeners.clear();
  }
}

export const wsService = new WebSocketService();