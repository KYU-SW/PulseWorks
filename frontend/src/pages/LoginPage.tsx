import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const GENERIC_LOGIN_ERROR = "이메일 또는 비밀번호가 올바르지 않습니다.";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const role = await login(email, password);
      if (role === "DOCTOR") {
        navigate("/doctor");
      } else if (role === "PATIENT") {
        navigate("/patient");
      } else {
        // NURSE / ADMIN_STAFF / SYSTEM_ADMIN: 이번 Task는 전용 화면이 없다.
        // 의사·환자 화면으로 잘못 보내지 않고, 임상정보 없는 안전한 안내
        // 화면으로 보낸다.
        navigate("/unsupported-role");
      }
    } catch {
      // 이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다 — 백엔드도
      // 동일한 401을 반환하므로 여기서도 일반적인 메시지만 보여준다. 입력했던
      // 비밀번호는 어디에도 다시 표시하거나 로그로 남기지 않는다.
      setError(GENERIC_LOGIN_ERROR);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1>EMR 프로토타입</h1>
      <p>의료IT학과 학부 3학년 2학기 설계 과목의 교육용 EMR 프로토타입입니다.</p>
      <p>
        이 시스템의 모든 환자·진료 데이터는 <strong>합성(가짜) 데이터</strong>이며,
        실제 의료기관 운영 목적으로 사용되지 않습니다.
      </p>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">이메일</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div>
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "로그인 중..." : "로그인"}
        </button>
      </form>

      {error && <p role="alert">{error}</p>}
    </div>
  );
}
