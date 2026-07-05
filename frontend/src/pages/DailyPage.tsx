import { Mic, RotateCcw, Share2 } from "lucide-react";
import { useState } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";

import { useAppState } from "../state/AppState";
import type { DestinationCategory } from "../types";
import { categoryLabels } from "../utils/labels";
import { speakJapanese } from "../utils/speech";

const commandButtons: Array<{ label: string; category: DestinationCategory }> = [
  { label: "スーパーに行きたい", category: "supermarket" },
  { label: "病院に行きたい", category: "hospital" },
  { label: "薬局に行きたい", category: "pharmacy" },
  { label: "市役所に行きたい", category: "city_hall" }
];

function detectCategory(command: string): DestinationCategory | null {
  if (command.includes("スーパー")) return "supermarket";
  if (command.includes("病院")) return "hospital";
  if (command.includes("薬局")) return "pharmacy";
  if (command.includes("市役所")) return "city_hall";
  return null;
}

export function DailyPage() {
  const { ensureRehearsals } = useAppState();
  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition } =
    useSpeechRecognition();
  const [answer, setAnswer] = useState("行きたい場所を選んでください。");
  const [permissionError, setPermissionError] = useState("");

  async function answerForCategory(category: DestinationCategory) {
    const tasks = await ensureRehearsals();
    const task = tasks.find((item) => item.destination_category === category) ?? tasks[0];
    const text = task
      ? task.voice_script_ja
      : `${categoryLabels[category]}のリハーサル情報はまだありません。家族と確認してください。`;
    setAnswer(text);
    speakJapanese(text);
  }

  async function handleSpokenCommand(command: string) {
    if (command.includes("もう一度")) {
      speakJapanese(answer);
      return;
    }
    if (command.includes("家族に共有")) {
      setAnswer(`${answer} 家族に共有する文章はリハーサル画面で確認できます。`);
      return;
    }
    const category = detectCategory(command);
    if (!category) {
      const text = "聞き取れませんでした。大きなボタンから選んでください。";
      setAnswer(text);
      speakJapanese(text);
      return;
    }
    await answerForCategory(category);
  }

  async function toggleListening() {
    if (!browserSupportsSpeechRecognition) {
      setPermissionError("このブラウザでは音声入力が使えません。下のボタンから選んでください。");
      return;
    }
    try {
      if (listening) {
        await SpeechRecognition.stopListening();
        await handleSpokenCommand(transcript);
      } else {
        resetTranscript();
        await SpeechRecognition.startListening({ language: "ja-JP", continuous: false });
      }
    } catch {
      setPermissionError("マイクの許可を確認してください。音声入力なしでも使えます。");
    }
  }

  return (
    <main className="app-shell flow-shell">
      <section className="flow-panel daily-panel">
        <h1>いつもの場所に行きたい</h1>
        <button className="mic-button" type="button" onClick={() => void toggleListening()}>
          <Mic aria-hidden="true" size={52} />
          {listening ? "話し終わったら押す" : "マイクを押して話す"}
        </button>
        {permissionError ? <p className="warning-text">{permissionError}</p> : null}
        <p className="daily-answer">{answer}</p>
        <div className="choice-grid">
          {commandButtons.map((command) => (
            <button
              className="choice-button"
              key={command.category}
              type="button"
              onClick={() => void answerForCategory(command.category)}
            >
              {command.label}
            </button>
          ))}
        </div>
        <div className="button-row two">
          <button className="icon-text-button" type="button" onClick={() => speakJapanese(answer)}>
            <RotateCcw aria-hidden="true" size={26} />
            もう一度
          </button>
          <button
            className="icon-text-button"
            type="button"
            onClick={() => setAnswer(`${answer} 家族に共有する文章はリハーサル画面で確認できます。`)}
          >
            <Share2 aria-hidden="true" size={26} />
            家族に共有
          </button>
        </div>
      </section>
    </main>
  );
}
