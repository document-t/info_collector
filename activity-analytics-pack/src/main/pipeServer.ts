import { createServer } from 'net';
import { SystemController } from './systemController';
import log from 'electron-log';

export function startPipeServer(controller: SystemController) {
  const server = createServer((socket) => {
    
    socket.setEncoding('utf8');
    let buffer = '';

    socket.on('data', (chunk) => {
      buffer += chunk;
      const messages = buffer.split('\n');
      buffer = messages.pop() || '';

      for (const msg of messages) {
        if (!msg.trim()) continue;
        try {
          const data = JSON.parse(msg);
          controller.handleRealtimeData(data);
        } catch {
          
        }
      }
    });

    
  });

  server.listen('\\\\?\\pipe\\ActivityAnalytics', () =>
    log.info('Pipe server started on \\\\.\\pipe\\ActivityAnalytics')
  );
  
}