import { BusFront, Mic } from "lucide-react";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <main className="app-shell home-shell">
      <section className="home-hero" aria-labelledby="home-title">
        <div>
          <h1 id="home-title">車なし生活リハーサル</h1>
          <p className="lead-text">
            免許返納の前に、車なしの毎日を小さく試します。結果は情報提供であり、返納を決めるものではありません。
          </p>
        </div>
        <div className="home-actions">
          <Link className="large-button primary" to="/onboarding">
            <BusFront aria-hidden="true" size={34} />
            車なし生活をためしてみる
          </Link>
          <Link className="large-button secondary" to="/daily">
            <Mic aria-hidden="true" size={34} />
            いつもの場所に行きたい
          </Link>
        </div>
      </section>
    </main>
  );
}
