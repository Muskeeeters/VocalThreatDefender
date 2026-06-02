from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os

from ml_pipeline.audio_processing import extract_acoustic_fingerprint
from ml_pipeline.text_analysis import VishingTextClassifier
from ml_pipeline.engine import calculate_vishing_risk

# Initialize the heavy model once inside the server memory
nlp_analyzer = VishingTextClassifier()

class LiveCallAnalysisView(APIView):
    def post(self, request, format=None):
        audio_file = request.FILES.get('audio')
        transcript_text = request.data.get('text', '')
        
        if not audio_file:
            return Response({"error": "No audio payload provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Temporarily save file chunk to process
        temp_path = f"temp_{audio_file.name}"
        with open(temp_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
                
        try:
            # 1. Run Audio Processing
            audio_meta = extract_acoustic_fingerprint(temp_path)
            
            # 2. Run NLP Text Processing
            text_meta = nlp_analyzer.analyze_transcript(transcript_text)
            
            # 3. Fuse Analytics
            evaluation = calculate_vishing_risk(audio_meta, text_meta)
            
            return Response(evaluation, status=status.HTTP_200_OK)
            
        finally:
            # Cleanup filesystem clean
            if os.path.exists(temp_path):
                os.remove(temp_path)