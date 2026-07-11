import { AlertTriangle, Mic, RotateCcw, Share2 } from "lucide-react";
import { useState } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";

import { AsyncErrorState } from "../components/AsyncErrorState";
import { MobileAppShell } from "../components/MobileAppShell";
import { useAppState } from "../state/AppState";
import type { DestinationCategory } from "../types";
import { speakJapanese } from "../utils/speech";

const commandButtons: Array<{ label: string; category: DestinationCategory }> = [
  { label: "スーパー", category: "supermarket" },
  { label: "病院", category: "hospital" },
  { label: "薬局", category: "pharmacy" },
  { label: "市役所", category: "city_hall" }
];

const missingTaskMessage = "この場所はまだ登録されていません。家族と確認してください。";
const helpMessage = "近くの人や家族に相談してください。無理に移動しないでください。";

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
  const [failedCategory, setFailedCategory] = useState<DestinationCategory | null>(null);

  async function answerForCategory(category: DestinationCategory) {
    setFailedCategory(null);
    try {
      const tasks = await ensureRehearsals();
      const task = tasks.find((item) => item.destination_category === category);
      const text = task ? task.voice_script_ja : missingTaskMessage;
      setAnswer(text);
      speakJapanese(text);
    } catch {
      setFailedCategory(category);
    }
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
    if (command.includes("困った")) {
      setAnswer(helpMessage);
      speakJapanese(helpMessage);
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

  function shareAnswer() {
    setAnswer(`${answer} 家族に共有する文章はリハーサル画面で確認できます。`);
  }

  function showHelp() {
    setAnswer(helpMessage);
    speakJapanese(helpMessage);
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
    <MobileAppShell title="いつもの場所に行きたい" className="daily-screen" showHomeReturn>
      <section className="daily-panel">
        <button className="mic-button" type="button" onClick={() => void toggleListening()}>
          <Mic aria-hidden="true" size={52} />
          {listening ? "話し終わったら押す" : "マイクを押して話す"}
        </button>
        {permissionError ? <p className="warning-text">{permissionError}</p> : null}
        {failedCategory ? (
          <AsyncErrorState onRetry={() => void answerForCategory(failedCategory)} />
        ) : null}
        <p className="daily-answer" aria-live="polite">
          {answer}
        </p>
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
        <div className="button-row daily-tools">
          <button className="icon-text-button" type="button" onClick={() => speakJapanese(answer)}>
            <RotateCcw aria-hidden="true" size={26} />
            もう一度
          </button>
          <button className="icon-text-button" type="button" onClick={shareAnswer}>
            <Share2 aria-hidden="true" size={26} />
            家族に共有
          </button>
          <button className="icon-text-button urgent" type="button" onClick={showHelp}>
            <AlertTriangle aria-hidden="true" size={26} />
            困った
          </button>
        </div>
      </section>
    </MobileAppShell>
  );
}
