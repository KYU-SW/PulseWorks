interface AppHeaderProps {
  brand?: React.ReactNode;
  actions?: React.ReactNode;
  children?: React.ReactNode; // Navigation 슬롯
}

export default function AppHeader({ brand, actions, children }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        <div className="app-header__brand">{brand}</div>
        {children}
        <div className="app-header__actions">{actions}</div>
      </div>
    </header>
  );
}
