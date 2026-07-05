import { Share2, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";

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

export function RehearsalPage() {
  const { rehearsalTasks, ensureRehearsals } = useAppState();
  const [loading, setLoading] = useState(!rehearsalTasks.length);
  const [shareMessage, setShareMessage] = useState("");

  useEffect(() => {
    if (rehearsalTasks.length) return;
    void ensureRehearsals().finally(() => setLoading(false));
  }, [ensureRehearsals, rehearsalTasks.length]);

  return (
    <main className="app-shell flow-shell">
      <section className="flow-panel">
        <h1>リハーサル</h1>
        {loading ? <p className="loading-text">リハーサルを作っています</p> : null}
        <div className="task-list">
          {rehearsalTasks.map((task) => (
            <article className="task-card" key={task.id}>
              <h2>{task.title_ja}</h2>
              <p>{task.memo_ja}</p>
              <div className="button-row two">
                <button
                  className="icon-text-button"
                  type="button"
                  onClick={() => speakJapanese(task.voice_script_ja)}
                >
                  <Volume2 aria-hidden="true" size={26} />
                  音声で聞く
                </button>
                <button
                  className="icon-text-button"
                  type="button"
                  onClick={() => void shareTask(task, setShareMessage)}
                >
                  <Share2 aria-hidden="true" size={26} />
                  家族に共有する
                </button>
              </div>
              {shareMessage ? <p className="muted">{task.family_share_text_ja}</p> : null}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
