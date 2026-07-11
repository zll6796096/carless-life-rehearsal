import { Check, ChevronLeft, ChevronRight, Home } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AsyncErrorState } from "../components/AsyncErrorState";
import { MobileAppShell } from "../components/MobileAppShell";
import { useAppState } from "../state/AppState";
import { categoryLabels } from "../utils/labels";

const stepTitles = ["お住まいを選びます", "よく行く場所", "歩く時間", "乗り換え"];

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
  const [loadError, setLoadError] = useState(false);

  const loadFixture = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      await ensureFixture();
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [ensureFixture]);

  useEffect(() => {
    void loadFixture();
  }, [loadFixture]);

  if (loadError) {
    return (
      <MobileAppShell title="読み込みエラー">
        <AsyncErrorState onRetry={() => void loadFixture()} />
      </MobileAppShell>
    );
  }

  if (loading || !fixture || !profile) {
    return (
      <MobileAppShell title="読み込んでいます">
        <p className="loading-text">読み込んでいます</p>
      </MobileAppShell>
    );
  }

  const bottomActions = (
    <>
      <button
        className="text-button back-button"
        type="button"
        onClick={() => (step === 0 ? navigate("/") : setStep(step - 1))}
      >
        <ChevronLeft aria-hidden="true" size={24} />
        戻る
      </button>
      {step < 3 ? (
        <button
          className="large-button primary compact"
          type="button"
          onClick={() => setStep(step + 1)}
        >
          次へ
          <ChevronRight aria-hidden="true" size={26} />
        </button>
      ) : (
        <button
          className="large-button primary compact"
          type="button"
          disabled={selectedDestinationIds.length === 0}
          onClick={() => navigate("/diagnosis")}
        >
          診断する
        </button>
      )}
    </>
  );

  return (
    <MobileAppShell
      title={stepTitles[step]}
      subtitle={`ステップ ${step + 1} / 4`}
      bottom={bottomActions}
      className="flow-screen"
    >
      <section className="wizard-screen">
        {step === 0 ? (
          <div className="wizard-block">
            <button className="demo-home-card selected" type="button" aria-pressed="true">
              <Home aria-hidden="true" size={30} />
              <span>
                <strong>{homeText || fixture.home_location.name}</strong>
                <small>{fixture.home_location.address}</small>
              </span>
            </button>
            <p className="warning-text">現在はデモ住所で動作します</p>
            <label className="large-label" htmlFor="home-location">
              表示名
            </label>
            <input
              id="home-location"
              className="large-input"
              value={homeText}
              onChange={(event) => setHomeText(event.target.value)}
              placeholder="例：デモ自宅"
            />
          </div>
        ) : null}

        {step === 1 ? (
          <div className="wizard-block">
            <div className="destination-list">
              {fixture.destinations.map((destination) => {
                const selected = selectedDestinationIds.includes(destination.id);
                return (
                  <button
                    className={`destination-card ${selected ? "selected" : ""}`}
                    key={destination.id}
                    type="button"
                    onClick={() => toggleDestination(destination)}
                  >
                    {selected ? <Check aria-hidden="true" size={28} /> : null}
                    <span className="category-label">{categoryLabels[destination.category]}</span>
                    <strong>{destination.name}</strong>
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
            {selectedDestinationIds.length === 0 ? (
              <p className="error-text" role="alert">
                少なくとも1つ選んでください。
              </p>
            ) : null}
          </div>
        ) : null}
      </section>
    </MobileAppShell>
  );
}
