import { Share2, Volume2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AsyncErrorState } from "../components/AsyncErrorState";
import { MobileAppShell } from "../components/MobileAppShell";
import { useAppState } from "../state/AppState";
import type { RehearsalTask } from "../types";
import { speakJapanese } from "../utils/speech";

async function shareTask(task: RehearsalTask, setMessage: (value: string) => void) {
  const shareNavigator = navigator as Navigator & {
    share?: (data: { text: string }) => Promise<void>;
    clipboard?: { writeText?: (text: string) => Promise<void> };
  };

  if (shareNavigator.share) {
    await shareNavigator.share({ text: task.family_share_text_ja });
    return;
  }
  await shareNavigator.clipboard?.writeText?.(task.family_share_text_ja).catch(() => undefined);
  setMessage("家族に共有する文章を表示しました。");
}

function splitMemoSentences(task: RehearsalTask) {
  return task.memo_ja
    .replace(/^\d+\.\s*/, "")
    .split("。")
    .map((sentence) => sentence.trim())
    .filter(Boolean);
}

function rehearsalDetails(task: RehearsalTask) {
  const sentences = splitMemoSentences(task);
  const departure = task.memo_ja.match(/(\d{1,2}時ごろ)出発/)?.[1] ?? "デモ目安";
  const outbound =
    sentences.find((sentence) => sentence.includes("行けます") || sentence.includes("へ行きます")) ??
    "デモ目安: 行きの詳細は音声で確認してください。";
  const returnTrip =
    sentences.find((sentence) => sentence.includes("帰り") || sentence.includes("戻れ")) ??
    "デモ目安: 帰りの詳細は家族と確認してください。";
  const missed =
    sentences.find((sentence) => sentence.includes("乗り遅れ")) ??
    "デモ目安: 乗り遅れたら、無理に移動せず家族と確認してください。";

  return { departure, outbound, returnTrip, missed };
}

export function RehearsalPage() {
  const { rehearsalTasks, ensureRehearsals } = useAppState();
  const [loading, setLoading] = useState(!rehearsalTasks.length);
  const [loadError, setLoadError] = useState(false);
  const [shareMessage, setShareMessage] = useState("");
  const [sharedTaskId, setSharedTaskId] = useState("");

  const loadRehearsals = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      await ensureRehearsals();
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [ensureRehearsals]);

  useEffect(() => {
    if (rehearsalTasks.length) return;
    void loadRehearsals();
  }, [loadRehearsals, rehearsalTasks.length]);

  return (
    <MobileAppShell title="リハーサル" className="rehearsal-screen" showHomeReturn>
      <section className="rehearsal-intro">
        <p className="main-message">まずは無理のない外出を1つだけ試しましょう。</p>
        {loading ? <p className="loading-text">リハーサルを作っています</p> : null}
        {loadError ? <AsyncErrorState onRetry={() => void loadRehearsals()} /> : null}
        <div className="task-list">
          {rehearsalTasks.map((task) => {
            const details = rehearsalDetails(task);
            return (
              <article className="task-card" key={task.id}>
                <h2>{task.title_ja}</h2>
                <p className="departure-label">出発目安: {details.departure}</p>
                <dl className="outing-memo">
                  <div>
                    <dt>行き</dt>
                    <dd>{details.outbound}</dd>
                  </div>
                  <div>
                    <dt>帰り</dt>
                    <dd>{details.returnTrip}</dd>
                  </div>
                  <div>
                    <dt>もし乗り遅れたら</dt>
                    <dd>{details.missed}</dd>
                  </div>
                </dl>
                <div className="button-row two">
                  <button
                    className="icon-text-button"
                    type="button"
                    onClick={() => speakJapanese(task.voice_script_ja)}
                  >
                    <Volume2 aria-hidden="true" size={24} />
                    音声で聞く
                  </button>
                  <button
                    className="icon-text-button"
                    type="button"
                    onClick={() => {
                      setSharedTaskId(task.id);
                      void shareTask(task, setShareMessage);
                    }}
                  >
                    <Share2 aria-hidden="true" size={24} />
                    家族に共有
                  </button>
                </div>
                {shareMessage && sharedTaskId === task.id ? (
                  <p className="muted share-preview">{task.family_share_text_ja}</p>
                ) : null}
              </article>
            );
          })}
        </div>
      </section>
    </MobileAppShell>
  );
}
