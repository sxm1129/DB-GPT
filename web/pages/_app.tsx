import { ChatContext, ChatContextProvider } from '@/app/chat-context';
import SideBar from '@/components/layout/side-bar';
import FloatHelper from '@/new-components/layout/FloatHelper';
import { STORAGE_LANG_KEY, STORAGE_USERINFO_KEY, STORAGE_USERINFO_VALID_TIME_KEY } from '@/utils/constants/index';
import { App, ConfigProvider, MappingAlgorithm, theme } from 'antd';
import enUS from 'antd/locale/en_US';
import zhCN from 'antd/locale/zh_CN';
import classNames from 'classnames';
import type { AppProps } from 'next/app';
import Head from 'next/head';
import { useRouter } from 'next/router';
import React, { useContext, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import '../app/i18n';
import '../nprogress.css';
import '../styles/globals.css';
// import TopProgressBar from '@/components/layout/top-progress-bar';

const antdDarkTheme: MappingAlgorithm = (seedToken, mapToken) => {
  return {
    ...theme.darkAlgorithm(seedToken, mapToken),
    colorBgBase: '#232734',
    colorBorder: '#828282',
    colorBgContainer: '#232734',
  };
};

function CssWrapper({ children }: { children: React.ReactElement }) {
  const { mode } = useContext(ChatContext);
  const { i18n } = useTranslation();

  useEffect(() => {
    if (mode) {
      document.body?.classList?.add(mode);
      if (mode === 'light') {
        document.body?.classList?.remove('dark');
      } else {
        document.body?.classList?.remove('light');
      }
    }
  }, [mode]);

  useEffect(() => {
    i18n.changeLanguage?.(window.localStorage.getItem(STORAGE_LANG_KEY) || 'zh');
  }, [i18n]);

  return (
    <div>
      {/* <TopProgressBar /> */}
      {children}
    </div>
  );
}

function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const { isMenuExpand, mode } = useContext(ChatContext);
  const { i18n } = useTranslation();
  const [isLogin, setIsLogin] = useState(false);

  const router = useRouter();

  // 登录检测
  const handleAuth = async () => {
    setIsLogin(false);
    // 如果已有登录信息，直接展示首页
    // if (localStorage.getItem(STORAGE_USERINFO_KEY)) {
    //   setIsLogin(true);
    //   return;
    // }

    // MOCK User info
    const user = {
      user_channel: `xSmartKG`,
      user_no: `001`,
      nick_name: `xSmartKG`,
    };
    if (user) {
      localStorage.setItem(STORAGE_USERINFO_KEY, JSON.stringify(user));
      localStorage.setItem(STORAGE_USERINFO_VALID_TIME_KEY, Date.now().toString());
      setIsLogin(true);
    }
  };

  useEffect(() => {
    handleAuth();
  }, []);

  if (!isLogin) {
    return null;
  }

  const renderContent = () => {
    if (router.pathname.includes('mobile')) {
      return <>{children}</>;
    }
    
    // For graph visualization page, use h-full instead of overflow-y-auto
    const isGraphPage = /\/knowledge\/graph/.test(router.pathname);

    
    return (
      <div className='flex w-screen h-screen overflow-hidden'>
        <Head>
          <meta name='viewport' content='initial-scale=1.0, width=device-width, maximum-scale=1' />
        </Head>
        {router.pathname !== '/construct/app/extra' && (
          <div className={classNames('transition-[width]', isMenuExpand ? 'w-60' : 'w-20', 'hidden', 'md:block')}>
            <SideBar />
          </div>
        )}
        <div className={classNames('flex flex-col flex-1 relative', isGraphPage ? 'h-full overflow-hidden' : 'overflow-y-auto')}>
          {children}
        </div>
        <FloatHelper />
      </div>
    );
  };

  return (
    <ConfigProvider
      locale={i18n.language === 'en' ? enUS : zhCN}
      theme={{
        token: {
          colorPrimary: '#2563EB',
          colorSuccess: '#52C41A',
          colorWarning: '#FAAD14',
          colorError: '#FF4D4F',
          colorInfo: '#3B82F6',
          borderRadius: 8,
          borderRadiusLG: 12,
          borderRadiusSM: 6,
          fontFamily: "'Poppins', 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          fontFamilyCode: "'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace",
          fontSize: 14,
          fontSizeHeading1: 32,
          fontSizeHeading2: 24,
          fontSizeHeading3: 20,
          lineHeight: 1.5,
          lineHeightHeading1: 1.2,
          lineHeightHeading2: 1.3,
          boxShadow: '0 2px 8px rgba(37, 99, 235, 0.08)',
          boxShadowSecondary: '0 4px 16px rgba(37, 99, 235, 0.12)',
        },
        components: {
          Button: {
            borderRadius: 8,
            controlHeight: 40,
            controlHeightLG: 48,
            controlHeightSM: 32,
            fontWeight: 500,
            primaryShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
          },
          Card: {
            borderRadius: 12,
            borderRadiusLG: 16,
            paddingLG: 24,
            boxShadow: '0 4px 16px rgba(37, 99, 235, 0.08)',
            boxShadowTertiary: '0 8px 24px rgba(37, 99, 235, 0.12)',
          },
          Input: {
            borderRadius: 8,
            controlHeight: 40,
            controlHeightLG: 48,
            paddingBlock: 8,
            paddingInline: 12,
          },
          Select: {
            borderRadius: 8,
            controlHeight: 40,
            controlHeightLG: 48,
          },
          Modal: {
            borderRadius: 16,
            boxShadow: '0 12px 32px rgba(37, 99, 235, 0.18)',
          },
          Drawer: {
            borderRadius: 16,
          },
          Segmented: {
            borderRadius: 10,
            trackPadding: 4,
          },
        },
        algorithm: mode === 'dark' ? antdDarkTheme : undefined,
      }}
    >
      <App>{renderContent()}</App>
    </ConfigProvider>
  );
}

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ChatContextProvider>
      <CssWrapper>
        <LayoutWrapper>
          <Component {...pageProps} />
        </LayoutWrapper>
      </CssWrapper>
    </ChatContextProvider>
  );
}

export default MyApp;
