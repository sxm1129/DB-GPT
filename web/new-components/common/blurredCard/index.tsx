import { EllipsisOutlined } from '@ant-design/icons';
import { Divider, DropDownProps, Dropdown, Tooltip, Typography } from 'antd';
import cls from 'classnames';
import { t } from 'i18next';
import Image from 'next/image';
import React from 'react';

import AppDefaultIcon from '../AppDefaultIcon';
import './style.css';

const BlurredCard: React.FC<{
  RightTop?: React.ReactNode;
  Tags?: React.ReactNode;
  LeftBottom?: React.ReactNode;
  RightBottom?: React.ReactNode;
  rightTopHover?: boolean;
  name: string;
  description: string | React.ReactNode;
  logo?: string;
  onClick?: () => void;
  className?: string;
  scene?: string;
  code?: string;
}> = ({
  RightTop,
  Tags,
  LeftBottom,
  RightBottom,
  onClick,
  rightTopHover = true,
  logo,
  name,
  description,
  className,
  scene,
  code,
}) => {
  if (typeof description === 'string') {
    description = (
      <p className='line-clamp-2 relative bottom-4 text-ellipsis min-h-[42px] text-sm text-theme-text/70 dark:text-white/70'>
        {description}
      </p>
    );
  }

  return (
    <div className={cls('flex justify-center mt-6 relative group w-1/3 px-2 mb-6', className)}>
      <div
        onClick={onClick}
        className={cls(
          'cursor-pointer transition-glass card-hover relative w-full h-full p-5 rounded-2xl',
          'glass-card',
          'shadow-glass-md hover:shadow-card-hover',
          'transform-gpu',
        )}
      >
        <div className='flex items-end relative bottom-8 justify-between w-full'>
          <div className='flex items-end gap-4 w-11/12  flex-1'>
            <div className='bg-white dark:bg-[#232734] rounded-2xl shadow-glass-md w-14 h-14 flex items-center p-3 transition-glass group-hover:shadow-glass-lg group-hover:scale-110'>
              {scene ? (
                <AppDefaultIcon scene={scene} width={14} height={14} />
              ) : (
                logo && (
                  <Image src={logo} width={44} height={44} alt={name} className='w-8 min-w-8 rounded-full max-w-none' />
                )
              )}
            </div>
            <div className='flex-1'>
              {/** 先简单判断下 */}
              {name.length > 6 ? (
                <Tooltip title={name}>
                  <span
                    className='line-clamp-1 text-ellipsis font-semibold text-base font-heading text-theme-text dark:text-white'
                    style={{
                      maxWidth: '60%',
                    }}
                  >
                    {name}
                  </span>
                </Tooltip>
              ) : (
                <span
                  className='line-clamp-1 text-ellipsis font-semibold text-base font-heading text-theme-text dark:text-white'
                  style={{
                    maxWidth: '60%',
                  }}
                >
                  {name}
                </span>
              )}
            </div>
          </div>
          <span
            className={cls('shrink-0', {
              hidden: rightTopHover,
              'group-hover:block': rightTopHover,
            })}
            onClick={e => {
              e.stopPropagation();
            }}
          >
            {RightTop}
          </span>
        </div>
        {description}
        <div className='relative bottom-2'>{Tags}</div>
        <div className='flex justify-between items-center'>
          <div>{LeftBottom}</div>
          <div>{RightBottom}</div>
        </div>
        {code && (
          <>
            <Divider className='my-3' />
            <Typography.Text copyable={true} className='absolute bottom-1 right-4 text-xs text-gray-500'>
              {code}
            </Typography.Text>
          </>
        )}
      </div>
    </div>
  );
};

const ChatButton: React.FC<{
  onClick?: () => void;
  Icon?: React.ReactNode | string;
  text?: string;
}> = ({ onClick, Icon = '/pictures/card_chat.png', text = t('start_chat') }) => {
  if (typeof Icon === 'string') {
    Icon = <Image src={Icon as string} alt={Icon as string} width={17} height={15} />;
  }

  return (
    <div
      className='flex items-center gap-1 text-default'
      onClick={e => {
        e.stopPropagation();
        onClick && onClick();
      }}
    >
      {Icon}
      <span>{text}</span>
    </div>
  );
};

const InnerDropdown: React.FC<{ menu: DropDownProps['menu'] }> = ({ menu }) => {
  return (
    <Dropdown
      menu={menu}
      getPopupContainer={node => node.parentNode as HTMLElement}
      placement='bottomRight'
      autoAdjustOverflow={false}
    >
      <EllipsisOutlined className='p-2 hover:bg-white hover:dark:bg-black rounded-md' />
    </Dropdown>
  );
};

export { ChatButton, InnerDropdown };
export default BlurredCard;
