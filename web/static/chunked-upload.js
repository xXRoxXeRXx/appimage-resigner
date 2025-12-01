/**
 * Chunked Upload Manager for Large Files
 * Provides resumable uploads with progress tracking
 */

class ChunkedUploader {
    constructor(options = {}) {
        this.chunkSize = options.chunkSize || 5 * 1024 * 1024; // 5MB default
        this.maxRetries = options.maxRetries || 3;
        this.parallelUploads = options.parallelUploads || 3;
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});
        
        this.uploadSessions = new Map();
    }
    
    /**
     * Upload file in chunks
     * @param {File} file - File to upload
     * @param {string} sessionId - Session ID
     * @param {string} fileType - File type (appimage, key, signature)
     * @returns {Promise<object>} Upload result
     */
    async uploadFile(file, sessionId, fileType = 'appimage') {
        const filename = file.name;
        const totalSize = file.size;
        
        try {
            // Initialize upload
            const initResponse = await this.initUpload(
                sessionId,
                filename,
                totalSize,
                fileType
            );
            
            const totalChunks = initResponse.total_chunks;
            const uploadId = `${sessionId}_${Date.now()}`;
            
            // Store upload session
            this.uploadSessions.set(uploadId, {
                sessionId,
                file,
                fileType,
                totalChunks,
                uploadedChunks: new Set(),
                failedChunks: new Map(),
                startTime: Date.now()
            });
            
            // Upload chunks with parallel processing
            await this.uploadChunks(uploadId, file, sessionId, totalChunks);
            
            // Complete upload
            const result = await this.completeUpload(sessionId, fileType);
            
            // Clean up
            this.uploadSessions.delete(uploadId);
            
            this.onComplete(result);
            return result;
            
        } catch (error) {
            console.error('Upload failed:', error);
            this.onError(error);
            throw error;
        }
    }
    
    /**
     * Initialize chunked upload
     */
    async initUpload(sessionId, filename, totalSize, fileType) {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('filename', filename);
        formData.append('total_size', totalSize);
        formData.append('file_type', fileType);
        
        const response = await fetch('/api/upload/init', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to initialize upload');
        }
        
        return await response.json();
    }
    
    /**
     * Upload all chunks with parallel processing
     */
    async uploadChunks(uploadId, file, sessionId, totalChunks) {
        const session = this.uploadSessions.get(uploadId);
        const chunks = [];
        
        // Create chunk tasks
        for (let i = 0; i < totalChunks; i++) {
            chunks.push(i);
        }
        
        // Process chunks in parallel batches
        const batchSize = this.parallelUploads;
        
        for (let i = 0; i < chunks.length; i += batchSize) {
            const batch = chunks.slice(i, i + batchSize);
            
            await Promise.all(
                batch.map(chunkNum =>
                    this.uploadChunk(uploadId, file, sessionId, chunkNum, totalChunks)
                )
            );
        }
    }
    
    /**
     * Upload a single chunk with retry logic
     */
    async uploadChunk(uploadId, file, sessionId, chunkNumber, totalChunks, retryCount = 0) {
        const session = this.uploadSessions.get(uploadId);
        
        // Calculate chunk boundaries
        const start = chunkNumber * this.chunkSize;
        const end = Math.min(start + this.chunkSize, file.size);
        const chunk = file.slice(start, end);
        
        try {
            // Calculate checksum
            const checksum = await this.calculateMD5(chunk);
            
            // Prepare form data
            const formData = new FormData();
            formData.append('chunk_number', chunkNumber);
            formData.append('checksum', checksum);
            formData.append('chunk', chunk);
            
            // Upload chunk
            const response = await fetch(`/api/upload/chunk/${sessionId}`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Chunk upload failed: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Mark chunk as uploaded
            session.uploadedChunks.add(chunkNumber);
            
            // Update progress
            const progress = (session.uploadedChunks.size / totalChunks) * 100;
            const uploadedBytes = session.uploadedChunks.size * this.chunkSize;
            const speed = this.calculateSpeed(session.startTime, uploadedBytes);
            const eta = this.calculateETA(file.size, uploadedBytes, speed);
            
            this.onProgress({
                progress: progress,
                uploadedChunks: session.uploadedChunks.size,
                totalChunks: totalChunks,
                speed: speed,
                eta: eta
            });
            
            return result;
            
        } catch (error) {
            console.error(`Chunk ${chunkNumber} upload failed:`, error);
            
            // Retry logic
            if (retryCount < this.maxRetries) {
                console.log(`Retrying chunk ${chunkNumber} (attempt ${retryCount + 1}/${this.maxRetries})`);
                await this.delay(1000 * (retryCount + 1)); // Exponential backoff
                return this.uploadChunk(uploadId, file, sessionId, chunkNumber, totalChunks, retryCount + 1);
            } else {
                session.failedChunks.set(chunkNumber, error);
                throw error;
            }
        }
    }
    
    /**
     * Complete chunked upload
     */
    async completeUpload(sessionId, fileType) {
        const formData = new FormData();
        formData.append('file_type', fileType);
        
        const response = await fetch(`/api/upload/complete/${sessionId}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to complete upload');
        }
        
        return await response.json();
    }
    
    /**
     * Calculate MD5 checksum of chunk
     */
    async calculateMD5(blob) {
        const buffer = await blob.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hashHex;
    }
    
    /**
     * Calculate upload speed in bytes/sec
     */
    calculateSpeed(startTime, uploadedBytes) {
        const elapsedSeconds = (Date.now() - startTime) / 1000;
        return elapsedSeconds > 0 ? uploadedBytes / elapsedSeconds : 0;
    }
    
    /**
     * Calculate estimated time remaining
     */
    calculateETA(totalSize, uploadedBytes, speed) {
        if (speed === 0) return Infinity;
        const remainingBytes = totalSize - uploadedBytes;
        return remainingBytes / speed;
    }
    
    /**
     * Format bytes to human readable
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    /**
     * Format speed to human readable
     */
    formatSpeed(bytesPerSecond) {
        return this.formatBytes(bytesPerSecond) + '/s';
    }
    
    /**
     * Format ETA to human readable
     */
    formatETA(seconds) {
        if (seconds === Infinity) return 'Calculating...';
        if (seconds < 60) return Math.round(seconds) + 's';
        if (seconds < 3600) return Math.round(seconds / 60) + 'm ' + Math.round(seconds % 60) + 's';
        return Math.round(seconds / 3600) + 'h ' + Math.round((seconds % 3600) / 60) + 'm';
    }
    
    /**
     * Utility delay function
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Resume failed upload
     */
    async resumeUpload(uploadId) {
        const session = this.uploadSessions.get(uploadId);
        if (!session) {
            throw new Error('Upload session not found');
        }
        
        // Retry failed chunks
        const failedChunkNumbers = Array.from(session.failedChunks.keys());
        
        for (const chunkNumber of failedChunkNumbers) {
            session.failedChunks.delete(chunkNumber);
            await this.uploadChunk(
                uploadId,
                session.file,
                session.sessionId,
                chunkNumber,
                session.totalChunks
            );
        }
    }
}

// Export for use in main app
if (typeof window !== 'undefined') {
    window.ChunkedUploader = ChunkedUploader;
}
