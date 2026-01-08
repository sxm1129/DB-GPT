import React from 'react';
import ColorfulXSmartKG from './colorful-xsmartkg';

interface Props {
  className?: string;
  isCollapsed?: boolean;
}

const XSmartKGLogo: React.FC<Props> = ({ className = '', isCollapsed = false }) => {
  return (
    <div className={`flex items-center gap-3 transition-all duration-300 ${className}`}>
      <div className="flex-shrink-0">
        <ColorfulXSmartKG size={isCollapsed ? 32 : 36} />
      </div>
      {!isCollapsed && (
        <div className="flex items-baseline font-heading tracking-tight select-none">
          <span className="text-2xl font-light text-theme-primary">x</span>
          <span className="text-2xl font-bold text-slate-900 dark:text-white ml-0.5">SmartKG</span>
        </div>
      )}
    </div>
  );
};

export default XSmartKGLogo;
