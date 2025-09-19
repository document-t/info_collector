import { createServer } from 'net';
import { SystemController } from './systemController';
import log from 'electron-log';

export function startPipeServer(controller: SystemController) {
  const server = createServer((socket) => {
    log.info('Client connected to pipe server');
    
    socket.setEncoding('utf8');
    let buffer = '';
    
    socket.on('data', (chunk) => {
      buffer += chunk;
      
      // 处理接收到的数据（假设每条数据以换行符分隔）
      const messages = buffer.split('\n');
      buffer = messages.pop() || '';
      
      for (const message of messages) {
        if (!message.trim()) continue;
        
        try {
          const data = JSON.parse(message);
          controller.handleRealtimeData(data);
        } catch (error) {
          log.error('Error parsing pipe data:', error);
          log.error('Invalid data:', message);
        }
      }
    });
    
    socket.on('end', () => {
      log.info('Client disconnected from pipe server');
    });
    
    socket.on('error', (error) => {
      log.error('Pipe server socket error:', error);
    });
  });
  
  server.listen('\\\\?\\pipe\\ActivityAnalytics', (err) => {
    if (err) {
      log.error('Failed to start pipe server:', err);
      return;
    }
    log.info('Pipe server started on \\\\.\\pipe\\ActivityAnalytics');
  });
  
  server.on('error', (error) => {
    log.error('Pipe server error:', error);
  });
  
  return server;
}
