#!/bin/bash
echo "Monitoring for audio/transcription activity..."
tail -f ../logs/backend.log | grep --line-buffered -E "audio|transcription|Whisper|Transcrib|chunk|encounter:start"