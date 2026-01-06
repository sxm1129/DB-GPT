import { ReadOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import { useRouter } from 'next/router';

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const Header: React.FC = () => {
  const { t } = useTranslation();
  const router = useRouter();

  const [showHeader, setShowHeader] = useState(true);

  useEffect(() => {
    if (
      router.pathname === '/construct/flow/canvas' ||
      router.pathname === '/construct/app/extra' ||
      (router.pathname === '/chat' && router.asPath !== '/chat')
    ) {
      setShowHeader(false);
    } else {
      setShowHeader(true);
    }
  }, [router]);

  if (!showHeader) {
    return null;
  }

  return (
    <header className='flex items-center justify-end fixed top-4 right-4 h-14 pr-4 z-50'>
      <div className='flex items-center gap-3 glass-light dark:glass-dark px-4 py-2 rounded-xl border border-theme-border dark:border-white/10 shadow-sm'>
        <a
          href='https://github.com/sxm1129/DB-GPT'
          target='_blank'
          className='flex items-center h-full transition-smooth hover:text-theme-primary dark:hover:text-theme-secondary'
          rel='noreferrer'
        >
          <Tooltip title={t('docs')}>
            <ReadOutlined className='text-lg' />
          </Tooltip>
        </a>

        <Tooltip title='帮助中心'>
          <span className='text-sm cursor-pointer transition-smooth hover:text-theme-primary dark:hover:text-theme-secondary'>
            帮助中心
          </span>
        </Tooltip>
      </div>
      {/* <UserBar /> */}
    </header>
  );
};

export default Header;
