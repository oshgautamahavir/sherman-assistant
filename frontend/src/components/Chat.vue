<template>
  <div class="chat-container">
    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.type]"
      >
        <div class="message-content">
          <div class="message-text">{{ message.text }}</div>
          <div v-if="message.sourceUrls && message.sourceUrls.length > 0" class="source-urls">
            <strong>Sources:</strong>
            <ul>
              <li v-for="(url, urlIndex) in message.sourceUrls" :key="urlIndex">
                <a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a>
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div v-if="loading" class="message assistant loading">
        <div class="message-content">
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>
    <form @submit.prevent="sendMessage" class="chat-input-form">
      <input
        v-model="inputMessage"
        type="text"
        placeholder="Ask a question about cruise destinations..."
        class="chat-input"
        :disabled="loading"
      />
      <button type="submit" class="send-button" :disabled="loading || !inputMessage.trim()">
        Send
      </button>
    </form>
  </div>
</template>

<script>
import { sendChatMessage } from '../services/api'

export default {
  name: 'Chat',
  data() {
    return {
      messages: [],
      inputMessage: '',
      loading: false
    }
  },
  methods: {
    async sendMessage() {
      if (!this.inputMessage.trim() || this.loading) return

      const question = this.inputMessage.trim()
      this.inputMessage = ''
      
      // Add user message
      this.messages.push({
        type: 'user',
        text: question
      })

      this.loading = true
      this.scrollToBottom()

      try {
        const response = await sendChatMessage(question)
        
        if (response.status === 200) {
          this.messages.push({
            type: 'assistant',
            text: response.answer,
            sourceUrls: response.source_urls || []
          })
        } else {
          this.messages.push({
            type: 'assistant',
            text: 'Sorry, I encountered an error. Please try again.'
          })
        }
      } catch (error) {
        console.error('Error sending message:', error)
        this.messages.push({
          type: 'assistant',
          text: 'Sorry, I encountered an error. Please try again.'
        })
      } finally {
        this.loading = false
        this.scrollToBottom()
      }
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    }
  },
  mounted() {
    // Welcome message
    this.messages.push({
      type: 'assistant',
      text: 'Hello! I\'m the Sherman Travel Assistant. Ask me anything about cruise destinations!'
    })
  }
}
</script>

<style scoped>
.chat-container {
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  height: 80vh;
  max-height: 800px;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message {
  display: flex;
  max-width: 80%;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-content {
  padding: 12px 16px;
  border-radius: 18px;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #667eea;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: #f0f0f0;
  color: #333;
  border-bottom-left-radius: 4px;
}

.message-text {
  line-height: 1.5;
  white-space: pre-wrap;
}

.source-urls {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  font-size: 0.9rem;
}

.source-urls ul {
  list-style: none;
  margin-top: 5px;
}

.source-urls li {
  margin: 5px 0;
}

.source-urls a {
  color: #667eea;
  text-decoration: none;
}

.source-urls a:hover {
  text-decoration: underline;
}

.loading-dots {
  display: flex;
  gap: 5px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.chat-input-form {
  display: flex;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  gap: 10px;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 25px;
  font-size: 16px;
  outline: none;
  transition: border-color 0.3s;
}

.chat-input:focus {
  border-color: #667eea;
}

.chat-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.send-button {
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 25px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s;
}

.send-button:hover:not(:disabled) {
  background: #5568d3;
}

.send-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>

