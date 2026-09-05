import { Check, ChevronLeft, ChevronRight, Home } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AsyncErrorState } from "../components/AsyncErrorState";
import { MobileAppShell } from "../components/MobileAppShell";
import { useAppState } from "../state/AppState";
import { categoryLabels } from "../utils/labels";
import { departureError } from "../utils/departures";

const stepTitles = ["お住まいを選びます", "よく行く場所", "歩く時間", "乗り換え"];

export function OnboardingPage() {
  const navigate = useNavigate();
  const {
    fixture,
    selectedDestinationIds,
    profile,
    homeText,
    outboundDeparture,
    returnDeparture,
    setDepartures,
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

  const isPilot = fixture.data_profile === "hakusan";
  const titles = isPilot ? [...stepTitles, "出発日時"] : stepTitles;
  const dateError = departureError(fixture, outboundDeparture, returnDeparture);
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
      {step < titles.length - 1 ? (
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
          disabled={selectedDestinationIds.length === 0 || Boolean(dateError)}
          onClick={() => navigate("/diagnosis")}
        >
          診断する
        </button>
      )}
    </>
  );

  return (
    <MobileAppShell
      title={isPilot && step === 0 ? "白山の公開テスト地点" : titles[step]}
      subtitle={`ステップ ${step + 1} / ${titles.length}`}
      bottom={bottomActions}
      className="flow-screen"
    >
      <div
        className="step-progress"
        role="progressbar"
        aria-label="設定の進み具合"
        aria-valuemin={1}
        aria-valuemax={titles.length}
        aria-valuenow={step + 1}
      >
        <span style={{ width: `${((step + 1) / titles.length) * 100}%` }} />
      </div>
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
            <p className="info-note" role="status">
              {isPilot ? "白山試用：公開テスト地点から計算します。ご自宅の診断ではありません。" : "現在はデモ住所で動作します"}
            </p>
            {!isPilot ? <>
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
            </> : null}
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
                    aria-pressed={selected}
                    onClick={() => toggleDestination(destination)}
                  >
                    <span className="destination-copy">
                      <span className="category-label">{categoryLabels[destination.category]}</span>
                      <strong>{destination.name}</strong>
                    </span>
                    <span className="selection-indicator" aria-hidden="true">
                      {selected ? <Check size={22} /> : null}
                    </span>
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

        {step === 4 && isPilot ? (
          <div className="wizard-block">
            <p className="info-note">日本時間（UTC+09:00）。各目的地へ同じ条件で個別に往復します。周遊計画ではありません。</p>
            <p>時刻表の対象期間：{fixture.pilot?.service_start} ～ {fixture.pilot?.service_end}</p>
            <label className="large-label" htmlFor="outbound-departure">行きの出発日時（日本時間）</label>
            <input id="outbound-departure" className="large-input" type="datetime-local"
              min={`${fixture.pilot?.service_start}T00:00`} max={`${fixture.pilot?.service_end}T23:59`}
              value={outboundDeparture} onChange={event => setDepartures(event.target.value, returnDeparture)} />
            <label className="large-label" htmlFor="return-departure">帰りの出発日時（日本時間）</label>
            <input id="return-departure" className="large-input" type="datetime-local"
              min={`${fixture.pilot?.service_start}T00:00`} max={`${fixture.pilot?.service_end}T23:59`}
              value={returnDeparture} onChange={event => setDepartures(outboundDeparture, event.target.value)} />
            {dateError ? <p role="status" className="error-text">{dateError}</p> : null}
            {selectedDestinationIds.length === 0 ? <p role="alert">少なくとも1つ選んでください。</p> : null}
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
