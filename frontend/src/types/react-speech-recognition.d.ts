declare module "react-speech-recognition" {
  const SpeechRecognition: {
    startListening: (options?: { language?: string; continuous?: boolean }) => Promise<void> | void;
    stopListening: () => Promise<void> | void;
  };

  export function useSpeechRecognition(): {
    transcript: string;
    listening: boolean;
    resetTranscript: () => void;
    browserSupportsSpeechRecognition: boolean;
  };

  export default SpeechRecognition;
}
