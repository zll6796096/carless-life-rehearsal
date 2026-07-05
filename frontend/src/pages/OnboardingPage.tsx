import { Check, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAppState } from "../state/AppState";

export function OnboardingPage() {
  const navigate = useNavigate();
  const {
    fixture,
    selectedDestinationIds,
    profile,
    homeText,
    setHomeText,
    toggleDestination,
    setWalkMinutes,
    setMaxTransfers,
    ensureFixture
  } = useAppState();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void ensureFixture().finally(() => setLoading(false));
  }, [ensureFixture]);

  if (loading || !fixture || !profile) {
    return <main className="app-shell">読み込んでいます</main>;
  }

  return (
    <main className="app-shell flow-shell">
      <section className="flow-panel">
        <p className="step-label">ステップ {step + 1} / 4</p>
        <h1>はじめに確認すること</h1>

        {step === 0 ? (
          <div className="wizard-block">
            <label className="large-label" htmlFor="home-location">
              自宅の住所
            </label>
            <input
              id="home-location"
              className="large-input"
              value={homeText}
              onChange={(event) => setHomeText(event.target.value)}
              placeholder="例：東京都デモ市1-2-3"
            />
          </div>
        ) : null}

        {step === 1 ? (
          <div className="wizard-block">
            <p className="large-label">よく行く場所</p>
            <div className="choice-grid">
              {fixture.destinations.map((destination) => {
                const selected = selectedDestinationIds.includes(destination.id);
                return (
                  <button
                    className={`choice-button ${selected ? "selected" : ""}`}
                    key={destination.id}
                    type="button"
                    onClick={() => toggleDestination(destination)}
                  >
                    {selected ? <Check aria-hidden="true" size={28} /> : null}
                    {destination.name}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="wizard-block">
            <p className="large-label">歩ける時間</p>
            <div className="choice-grid">
              {[
                ["5分くらい", 5],
                ["10分くらい", 10],
                ["15分くらい", 15]
              ].map(([label, value]) => (
                <button
                  className={`choice-button ${profile.walk_minutes === value ? "selected" : ""}`}
                  key={label}
                  type="button"
                  onClick={() => setWalkMinutes(Number(value))}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="wizard-block">
            <p className="large-label">乗り換え</p>
            <div className="choice-grid">
              <button
                className={`choice-button ${profile.max_transfers === 0 ? "selected" : ""}`}
                type="button"
                onClick={() => setMaxTransfers(0)}
              >
                乗り換えなしがよい
              </button>
              <button
                className={`choice-button ${profile.max_transfers === 1 ? "selected" : ""}`}
                type="button"
                onClick={() => setMaxTransfers(1)}
              >
                1回までならよい
              </button>
            </div>
          </div>
        ) : null}

        <div className="nav-row">
          {step > 0 ? (
            <button className="text-button" type="button" onClick={() => setStep(step - 1)}>
              戻る
            </button>
          ) : (
            <span />
          )}
          {step < 3 ? (
            <button className="large-button primary compact" type="button" onClick={() => setStep(step + 1)}>
              次へ
              <ChevronRight aria-hidden="true" size={28} />
            </button>
          ) : (
            <button
              className="large-button primary compact"
              type="button"
              onClick={() => navigate("/diagnosis")}
            >
              診断する
            </button>
          )}
        </div>
      </section>
    </main>
  );
}
