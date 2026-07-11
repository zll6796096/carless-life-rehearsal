import { ChevronLeft } from "lucide-react";
import { Link } from "react-router-dom";

export function HomeReturnLink() {
  return (
    <Link className="home-return-link" to="/">
      <ChevronLeft aria-hidden="true" size={24} />
      ホームへ戻る
    </Link>
  );
}
