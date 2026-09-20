import PageContainer from "./PageContainer";

const SYNTHETIC_DATA_NOTICE_TEXT =
  "이 시스템은 교육용 합성 데이터를 사용합니다. 실제 진료에 사용할 수 없습니다.";

interface AppShellProps {
  header?: React.ReactNode;
  // 정상적인 안내 문구이므로 role="alert"를 자동으로 붙이지 않는다.
  showSyntheticDataNotice?: boolean;
  children: React.ReactNode;
}

// AppShell은 인증·권한을 직접 판단하지 않고 API도 호출하지 않는다 —
// 순수 레이아웃 조합만 담당한다. 실제 접근제어는 여전히 ProtectedRoute와
// 백엔드가 담당한다.
export default function AppShell({ header, showSyntheticDataNotice = false, children }: AppShellProps) {
  return (
    <div className="app-shell">
      {header}
      {showSyntheticDataNotice && (
        <p className="synthetic-data-banner">{SYNTHETIC_DATA_NOTICE_TEXT}</p>
      )}
      <PageContainer>{children}</PageContainer>
    </div>
  );
}
