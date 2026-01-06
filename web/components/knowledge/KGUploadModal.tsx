import React, { useState, useEffect, useRef } from 'react';
import { Modal, Upload, Form, Input, Button, Progress, message, Space, List, Tag, Table, Radio } from 'antd';
import { InboxOutlined, LoadingOutlined, CheckCircleOutlined, SyncOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { uploadKGFiles, getKGTasks, KGTaskResponse } from '@/client/api/knowledge';

const { Dragger } = Upload;

interface KGUploadModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess?: () => void;
  spaceName?: string;
}

const KGUploadModal: React.FC<KGUploadModalProps> = ({ visible, onCancel, onSuccess, spaceName }) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>('');
  const [historyTasks, setHistoryTasks] = useState<KGTaskResponse[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (visible) {
      fetchHistory();
    }
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [visible]);

  const fetchHistory = async () => {
    try {
      const [err, res] = await getKGTasks({ page: 1, page_size: 5 });
      if (res) setHistoryTasks(res.tasks);
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.error('请先选择 Excel 文件');
      return;
    }
    
    const values = await form.validateFields();
    setUploading(true);
    setTaskId(null);
    setProgress(0);
    setTaskStatus('pending');
    
    const formData = new FormData();
    fileList.forEach(file => {
      formData.append('files', file as any);
    });
    formData.append('graph_space_name', values.graph_space_name);
    formData.append('excel_mode', values.excel_mode);
    if (values.custom_prompt) {
      formData.append('custom_prompt', values.custom_prompt);
    }

    try {
      const [err, res] = await uploadKGFiles(formData);
      if (err) {
        message.error('上传失败');
        setUploading(false);
        return;
      }
      
      if (res && res.task_id) {
        setTaskId(res.task_id);
        startWebSocket(res.task_id);
      }
    } catch (e) {
      message.error('请求异常');
      setUploading(false);
    }
  };

  const startWebSocket = (tid: string) => {
    // 动态确定 WS 地址
    const isHttps = window.location.protocol === 'https:';
    const host = window.location.host;
    const wsUrl = `${isHttps ? 'wss' : 'ws'}://${host}/api/v2/serve/knowledge_graph/ws/${tid}`;
    
    console.log('Connecting to WS:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.progress !== undefined) setProgress(Math.floor(data.progress * 100));
        if (data.status) setTaskStatus(data.status);
        if (data.message) setStatusMsg(data.message);
        
        if (data.status === 'completed' || data.status === 'failed') {
          setUploading(false);
          if (data.status === 'completed') {
            message.success('知识图谱构建成功！');
            if (onSuccess) onSuccess();
          }
          ws.close();
        }
      } catch (e) {
        console.error('WS parse error', e);
      }
    };

    ws.onerror = (e) => {
      console.error('WS Error', e);
      setUploading(false);
    };
  };

  const columns = [
    { title: '任务ID', dataIndex: 'task_id', key: 'id', ellipsis: true },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        let color = 'gold';
        if (status === 'completed') color = 'green';
        if (status === 'failed') color = 'red';
        return <Tag color={color}>{status.toUpperCase()}</Tag>;
      }
    },
    { title: '进度', dataIndex: 'progress', key: 'progress', render: (p: number) => `${Math.floor(p * 100)}%` },
    { title: '创建时间', dataIndex: 'gmt_created', key: 'time' },
  ];

  return (
    <Modal
      title="Upload & Build Knowledge Graph"
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={null}
      destroyOnClose
    >
      {!taskId && !uploading ? (
        <Form form={form} layout="vertical" initialValues={{ graph_space_name: spaceName || '', excel_mode: 'auto' }}>
          <Form.Item name="graph_space_name" label="Graph Space Name" rules={[{ required: true }]}>
            <Input placeholder="Enter graph space name (e.g. MyKnowledgeGraph)" />
          </Form.Item>
          
          <Form.Item name="excel_mode" label="Excel Parsing Mode">
            <Radio.Group>
              <Radio value="auto">Auto (LLM Semantic)</Radio>
              <Radio value="manual">Structured (Column Mapping)</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="custom_prompt" label="Custom Extraction Prompt (Optional)">
            <Input.TextArea placeholder="Default: Extract entities and relations as triplets..." rows={3} />
          </Form.Item>

          <Form.Item label="Excel Files">
            <Dragger
              multiple
              accept=".xlsx,.xls"
              fileList={fileList}
              onRemove={(file) => {
                const index = fileList.indexOf(file);
                const newFileList = fileList.slice();
                newFileList.splice(index, 1);
                setFileList(newFileList);
              }}
              beforeUpload={(file) => {
                setFileList([...fileList, file]);
                return false;
              }}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">Click or drag Excel files to this area to upload</p>
              <p className="ant-upload-hint">Support for single or bulk upload. Strictly prohibited from uploading company data or other sensitive files.</p>
            </Dragger>
          </Form.Item>

          <div style={{ textAlign: 'right', marginTop: 24 }}>
            <Button onClick={onCancel} style={{ marginRight: 8 }}>Cancel</Button>
            <Button type="primary" onClick={handleUpload} loading={uploading}>Start Build</Button>
          </div>
          
          <div style={{ marginTop: 32 }}>
            <h4>Recent Tasks</h4>
            <Table dataSource={historyTasks} columns={columns} size="small" pagination={false} rowKey="task_id" />
          </div>
        </Form>
      ) : (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {taskStatus === 'running' || taskStatus === 'pending' ? <LoadingOutlined style={{ fontSize: 48 }} spin /> : null}
            {taskStatus === 'completed' ? <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} /> : null}
            {taskStatus === 'failed' ? <CloseCircleOutlined style={{ fontSize: 48, color: '#ff4d4f' }} /> : null}
            
            <h3 style={{ margin: 0 }}>{taskStatus?.toUpperCase()}</h3>
            <p style={{ color: '#666' }}>{statusMsg || 'Initializing task...'}</p>
            
            <Progress percent={progress} status={taskStatus === 'failed' ? 'exception' : 'active'} strokeWidth={10} />
            
            <div style={{ marginTop: 24 }}>
              <Button onClick={() => { setTaskId(null); setUploading(false); fetchHistory(); }}>Back</Button>
            </div>
          </Space>
        </div>
      )}
    </Modal>
  );
};

export default KGUploadModal;
