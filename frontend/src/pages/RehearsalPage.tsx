import { Share2, Volume2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncErrorState } from "../components/AsyncErrorState";
import { MobileAppShell } from "../components/MobileAppShell";
import { PilotNotice } from "../components/PilotNotice";
import { useAppState } from "../state/AppState";
import type { RehearsalTask } from "../types";
import { speakJapanese } from "../utils/speech";

async function shareTask(task: RehearsalTask, setMessage: (value: string) => void) {
  const shareNavigator = navigator as Navigator & {
    share?: (data: { text: string }) => Promise<void>;
    clipboard?: { writeText?: (text: string) => Promise<void> };
  };

  try {
    if (shareNavigator.share) {
      await shareNavigator.share({ text: task.family_share_text_ja });
      setMessage("共有操作が完了しました。相手への到達はご確認ください。");
    } else if (shareNavigator.clipboard?.writeText) {
      await shareNavigator.clipboard.writeText(task.family_share_text_ja);
      setMessage("共有する文章をコピーしました。まだ送信していません。");
    } else setMessage("共有機能が使えません。下の文章を確認してください。まだ送信していません。");
  } catch {
    setMessage("共有は完了していません。キャンセルまたは権限をご確認ください。下の文章は引き続き確認できます。");
  }
}

function splitMemoSentences(task: RehearsalTask) {
  return task.memo_ja
    .replace(/^\d+\.\s*/, "")
    .split("。")
    .map((sentence) => sentence.trim())
    .filter(Boolean);
}

function rehearsalDetails(task: RehearsalTask) {
  if (task.data_source === "routing_provider") return {
    departure: task.outbound_departure ? japanDate(task.outbound_departure) : "未確認",
    outbound: task.outbound_summary_ja ?? "行きの詳細は未確認です。",
    returnTrip: task.return_summary_ja ?? "帰りの詳細は未確認です。",
    missed: task.missed_connection_ja ?? "代替便は未確認です。再診断してください。"
  };
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

function japanDate(value: string): string {
  const date = new Date(value);
  return new Date(date.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 16).replace("T", " ");
}

export function RehearsalPage() {
  const { rehearsalTasks, ensureRehearsals, fixture, rehearsalRecords, recordRehearsal } = useAppState();
  const pilot = fixture?.data_profile === "hakusan";
  const [notes, setNotes] = useState<Record<string, string>>({});
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
        {pilot ? <>
          <p className="info-note">指定日の練習候補です。各候補は別々の往復案です。記録はこのページを開いている間だけ保存され、再読み込み・条件変更で消えます。記録しても安全確認済みにはなりません。</p>
          <details><summary>データと未確認事項</summary><PilotNotice fixture={fixture} /></details>
          <Link to="/onboarding">日時・条件を変更して再診断</Link>
          <p><Link to="/map">家族レポートで記録を確認</Link></p>
        </> : null}
        {loading ? <p className="loading-text">リハーサルを作っています</p> : null}
        {loadError ? <AsyncErrorState onRetry={() => void loadRehearsals()} /> : null}
        {!loading && !loadError && !rehearsalTasks.length ? <p role="status">練習できる経路が確認できません。日時や条件を変更して再診断してください。</p> : null}
        <div className="task-list">
          {rehearsalTasks.map((task, taskIndex) => {
            const details = rehearsalDetails(task);
            return (
              <article className="task-card" key={task.id}>
                <h2>{task.title_ja}</h2>
                {task.data_source === "routing_provider" ? <>
                  <p>日本時間・行きの出発：{details.departure}</p>
                  <p>帰りの出発：{task.return_departure ? japanDate(task.return_departure) : "未確認"}</p>
                </> : <p className="departure-label">出発目安: {details.departure}</p>}
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
                <div className="rehearsal-actions" role="group" aria-label="リハーサルの操作">
                  <button
                    className={
                      taskIndex === 0
                        ? "large-button primary rehearsal-listen"
                        : "icon-text-button rehearsal-listen"
                    }
                    type="button"
                    onClick={() => speakJapanese(task.voice_script_ja)}
                  >
                    <Volume2 aria-hidden="true" size={24} />
                    音声で聞く
                  </button>
                  <button
                    className="icon-text-button rehearsal-share"
                    type="button"
                    onClick={() => {
                      setSharedTaskId(task.id);
                      setShareMessage("共有する文章のプレビューです。まだ送信していません。");
                    }}
                  >
                    <Share2 aria-hidden="true" size={24} />
                    家族に共有
                  </button>
                </div>
                {shareMessage && sharedTaskId === task.id ? (
                  <div>
                    <p role="status">{shareMessage}</p>
                    <p className="muted share-preview">{task.family_share_text_ja}</p>
                    <button className="icon-text-button" type="button" onClick={() => void shareTask(task, setShareMessage)}>共有アプリを開く・コピー</button>
                  </div>
                ) : null}
                {pilot ? <section aria-label={`${task.destination_name}の練習記録`}>
                  <label htmlFor={`note-${task.id}`}>{task.destination_name}のメモ</label>
                  <textarea id={`note-${task.id}`} className="large-input" maxLength={500}
                    value={notes[task.id] ?? rehearsalRecords[task.id]?.note ?? ""}
                    onChange={event => setNotes(current => ({...current, [task.id]: event.target.value}))} />
                  <div className="button-row">
                    <button className="icon-text-button" type="button" aria-label={`${task.destination_name}：完了と記録`}
                      onClick={() => recordRehearsal(task.id, "completed", notes[task.id] ?? rehearsalRecords[task.id]?.note ?? "")}>練習を完了と記録</button>
                    <button className="icon-text-button" type="button" aria-label={`${task.destination_name}：支援が必要と記録`}
                      onClick={() => recordRehearsal(task.id, "needs_support", notes[task.id] ?? rehearsalRecords[task.id]?.note ?? "")}>支援が必要と記録</button>
                  </div>
                  {rehearsalRecords[task.id] ? <p role="status">記録済み：{rehearsalRecords[task.id].outcome === "completed" ? "練習完了（自己申告）" : "支援が必要"}</p> : null}
                </section> : null}
              </article>
            );
          })}
        </div>
      </section>
    </MobileAppShell>
  );
}
