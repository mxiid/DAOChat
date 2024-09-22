import React, { useState } from 'react';
import { TextField, Button, Paper, Typography } from '@material-ui/core';
import axios from 'axios';

const Chat = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');

    const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { text: input, user: true };
    setMessages([...messages, userMessage]);
    setInput('');

    try {
        const response = await axios.post('http://localhost:8000/ask', { text: input });
        const botMessage = { text: response.data.answer, user: false };
        setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
        console.error('Error:', error);
    }
    };

    return (
    <Paper elevation={3} style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        <Typography variant="h4" gutterBottom>
        RAG Chatbot
        </Typography>
        <div style={{ height: '400px', overflowY: 'auto', marginBottom: '20px' }}>
        {messages.map((message, index) => (
            <div key={index} style={{ textAlign: message.user ? 'right' : 'left', margin: '10px 0' }}>
            <Paper elevation={1} style={{ display: 'inline-block', padding: '10px', backgroundColor: message.user ? '#e3f2fd' : '#f1f8e9' }}>
                <Typography>{message.text}</Typography>
            </Paper>
            </div>
        ))}
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex' }}>
        <TextField
            fullWidth
            variant="outlined"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
        />
        <Button type="submit" variant="contained" color="primary" style={{ marginLeft: '10px' }}>
            Send
        </Button>
        </form>
    </Paper>
    );
};

export default Chat;