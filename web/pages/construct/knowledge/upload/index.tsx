import React, { useState, useEffect, useRef } from 'react';
import { 
  Card, Upload, Form, Input, Button, Progress, message, Space, Tag, Radio, 
  AutoComplete, Spin, Row, Col, Typography, Divider, Drawer, Select, Tooltip, Modal, Empty
} from 'antd';
import { 
  InboxOutlined, LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined,
  CloudUploadOutlined, DatabaseOutlined, BarChartOutlined, ArrowLeftOutlined,
  EyeOutlined, ReloadOutlined, DeleteOutlined, HistoryOutlined
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { uploadKGFiles, getKGTasks, getGraphSpaces, deleteKGTask, KGTaskResponse } from '@/client/api/knowledge';
import { useRouter } from 'next/router';
import { 
  Graphin, 
} from '@antv/graphin';
import { apiInterceptors, getGraphVis } from '@/client/api';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography; // Added Paragraph here
const { Option } = Select;

// 内置 Prompt 模板
const PROMPT_TEMPLATES = [
  { key: 'default', label: '📝 默认模板', prompt: '' },
  { key: 'person', label: '👤 人物关系', prompt: '请从文本中提取人物实体（如姓名、职位）以及人物之间的关系（如同事、上下级、家庭关系等）。' },
  { key: 'company', label: '🏢 企业关系', prompt: '请提取公司实体、负责人、商业关系(投资、收购、合作等)以及公司属性(行业、地址等)。' },
  { key: 'knowledge', label: '📚 知识概念', prompt: '请提取文本中的概念、术语以及它们之间的关系(包含、属于、相关等)。' },
  { key: 'event', label: '📅 事件提取', prompt: '请提取文本中的事件、参与者、时间、地点以及事件之间的因果关系。' },
];

// xSmartKG 品牌色系
const brandColors = {
  primary: '#1e88e5',
  primaryDark: '#1565c0',
  primaryLight: '#42a5f5',
  secondary: '#26c6da',
  gradient: 'linear-gradient(135deg, #1e88e5 0%, #26c6da 100%)',
  bgLight: 'linear-gradient(180deg, #f0f7ff 0%, #ffffff 100%)',
  cardBg: 'rgba(255, 255, 255, 0.95)',
  glassBg: 'rgba(255, 255, 255, 0.7)',
};

// 图谱预览组件 (缩略图)
const GraphPreview: React.FC<{ spaceName: string; refreshTrigger?: number }> = ({ spaceName, refreshTrigger }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!spaceName) return;
    const fetchGraph = async () => {
      setLoading(true);
      try {
        const [_, res] = await apiInterceptors(getGraphVis(spaceName, { limit: 50 }));
        if (res) {
          setData({
            nodes: res.nodes.map((n: any) => ({ id: n.id, data: n })),
            edges: res.edges.map((e: any) => ({ source: e.source, target: e.target, data: e }))
          });
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchGraph();
  }, [spaceName, refreshTrigger]);

  if (!spaceName) return <Empty description="选择空间以查看预览" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  if (loading) return <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin /></div>;
  if (!data || data.nodes.length === 0) return <Empty description="该空间尚无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;

  const options = {
    data,
    layout: { type: 'force', preventOverlap: true },
    autoFit: 'center',
    node: {
      style: (d: any) => ({
        labelText: d.data.name,
        labelFontSize: 10,
        size: 20,
        fill: '#1e88e5',
        labelBackground: true,
        labelBackgroundFill: '#fff',
      })
    },
    edge: {
      style: {
        endArrow: true,
        lineWidth: 1,
        stroke: '#e2e2e2'
      }
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element']
  };

  return (
    <div style={{ height: 300, background: '#fcfcfc', borderRadius: 8, border: '1px solid #f0f0f0', overflow: 'hidden' }}>
      <Graphin options={options} />
    </div>
  );
};

// AWEL 工作流配置弹窗
const AWELWorkflowModal: React.FC<{ visible: boolean; onCancel: () => void; onOk: (config: any) => void }> = ({ visible, onCancel, onOk }) => {
  const [config, setConfig] = useState('{\n  "extract_node": "kg_extraction",\n  "import_node": "tugraph_import",\n  "max_chunks": 100\n}');
  return (
    <Modal
      title="AWEL Workflow Configuration"
      open={visible} // Changed visible to open for Ant Design v5
      onCancel={onCancel}
      onOk={() => {
        try {
          const parsed = JSON.parse(config);
          onOk(parsed);
          onCancel();
        } catch (e) {
          message.error('Invalid JSON format');
        }
      }}
    >
      <Paragraph>您可以在此动态调整 AWEL 工作流的节点配置（JSON 格式）。</Paragraph>
      <Input.TextArea 
        rows={10} 
        value={config} 
        onChange={(e) => setConfig(e.target.value)}
        style={{ fontFamily: 'monospace', fontSize: 12 }}
      />
    </Modal>
  );
};

// 简单的数字动画组件
const AnimatedCounter: React.FC<{ value: number }> = ({ value }) => {
  const [displayValue, setDisplayValue] = useState(0);
  
  useEffect(() => {
    let startTimestamp: number | null = null;
    const duration = 1000; // 1秒动画
    const startValue = displayValue;
    
    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const current = Math.floor(progress * (value - startValue) + startValue);
      setDisplayValue(current);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    
    window.requestAnimationFrame(step);
  }, [value]);

  return <span>{displayValue.toLocaleString()}</span>;
};

const KGUploadPage: React.FC = () => {
  const router = useRouter();
  const [form] = Form.useForm();
  
  // 状态
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>('');
  const [entitiesCount, setEntitiesCount] = useState<number>(0);
  const [relationsCount, setRelationsCount] = useState<number>(0);
  const [taskFiles, setTaskFiles] = useState<any[]>([]);
  const [excelMode, setExcelMode] = useState<string>('auto');
  const [graphSpaces, setGraphSpaces] = useState<string[]>([]);
  const [loadingSpaces, setLoadingSpaces] = useState(false);
  const [historyTasks, setHistoryTasks] = useState<KGTaskResponse[]>([]);
  const [selectedSpace, setSelectedSpace] = useState<string>('');
  const [columnMapping, setColumnMapping] = useState({
    subjectColumn: '',
    predicate: '',
    objectColumn: ''
  });
  const [selectedPromptTemplate, setSelectedPromptTemplate] = useState('default');
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<KGTaskResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [awelModalVisible, setAwelModalVisible] = useState(false);
  const [workflowConfig, setWorkflowConfig] = useState<any>(null);
  const [graphRefresh, setGraphRefresh] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetchGraphSpaces();
    fetchHistory();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [statusFilter]);

  const fetchGraphSpaces = async () => {
    setLoadingSpaces(true);
    try {
      const [err, res] = await apiInterceptors(getGraphSpaces());
      if (res && res.spaces) {
        setGraphSpaces(res.spaces);
      }
    } catch (e) {
      console.error('Failed to fetch graph spaces', e);
    } finally {
      setLoadingSpaces(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const [err, res] = await apiInterceptors(getKGTasks({ 
        page: 1, 
        page_size: 10,
        status: statusFilter === 'all' ? undefined : statusFilter 
      }));
      if (res) setHistoryTasks(res.tasks);
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.error('请先选择文件');
      return;
    }
    
    const values = await form.validateFields();
    setUploading(true);
    setTaskId(null);
    setProgress(0);
    setTaskStatus('pending');
    setEntitiesCount(0);
    setRelationsCount(0);
    
    const formData = new FormData();
    fileList.forEach(file => {
      formData.append('files', file as any);
    });
    formData.append('graph_space_name', values.graph_space_name);
    formData.append('excel_mode', excelMode);
    if (values.custom_prompt) {
      formData.append('custom_prompt', values.custom_prompt);
    }
    if (excelMode === 'mapping') {
      const mapping = {
        entity_columns: [columnMapping.subjectColumn, columnMapping.objectColumn].filter(Boolean),
        relation_configs: [
          {
            subject_column: columnMapping.subjectColumn,
            predicate: columnMapping.predicate,
            object_column: columnMapping.objectColumn
          }
        ]
      };
      formData.append('column_mapping', JSON.stringify(mapping));
    }
    if (workflowConfig) {
      formData.append('workflow_config', JSON.stringify(workflowConfig));
    }

    try {
      const [err, res] = await apiInterceptors(uploadKGFiles(formData));
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

  const startWebSocket = (tid: string, retryCount = 0) => {
    if (retryCount > 10) {
      console.error('Max WS reconnection attempts reached');
      return;
    }

    const isHttps = window.location.protocol === 'https:';
    const host = window.location.host;
    const wsUrl = `${isHttps ? 'wss' : 'ws'}://${host}/api/v2/serve/knowledge_graph/ws/${tid}`;
    
    console.log(`Connecting to WS: ${wsUrl} (attempt ${retryCount + 1})`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.progress !== undefined) setProgress(Math.floor(data.progress));
        if (data.status) setTaskStatus(data.status);
        if (data.message) setStatusMsg(data.message);
        if (data.entities_count !== undefined) setEntitiesCount(data.entities_count);
        if (data.relations_count !== undefined) setRelationsCount(data.relations_count);
        if (data.file_names) setTaskFiles(data.file_names);
        
        if (data.status === 'completed' || data.status === 'failed') {
          setUploading(false);
          fetchHistory();
          if (data.status === 'completed') {
            message.success('知识图谱构建成功！');
            setGraphRefresh(prev => prev + 1);
          } else {
            message.error(`构建失败: ${data.message || '未知错误'}`);
          }
          ws.close();
        }
      } catch (e) {
        console.error('WS parse error', e);
      }
    };

    ws.onclose = () => {
      console.log('WS connection closed');
      // 如果上传中且未完成/未失败，则尝试重连
      if (uploading && taskStatus !== 'completed' && taskStatus !== 'failed') {
        setTimeout(() => {
          startWebSocket(tid, retryCount + 1);
        }, 3000);
      }
    };

    ws.onerror = (e) => {
      console.error('WS Error', e);
    };
  };

  const resetTask = () => {
    setTaskId(null);
    setUploading(false);
    setProgress(0);
    setTaskStatus(null);
    setEntitiesCount(0);
    setRelationsCount(0);
    setFileList([]);
  };

  const handleDeleteTask = (task: KGTaskResponse) => {
    Modal.confirm({
      title: '确认删除任务？',
      content: `确定要删除任务 "${task.graph_space_name}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        const [err, res] = await deleteKGTask(task.task_id);
        if (err) {
          message.error('删除失败');
          return;
        }
        message.success('任务已删除');
        setDrawerVisible(false);
        fetchHistory();
      }
    });
  };


  return (
    <div className="scrollbar-default" style={{ 
      height: '100%', 
      background: brandColors.bgLight,
      padding: '24px',
      overflowY: 'auto'
    }}>
      {/* 顶部标题栏 */}
      <div style={{ 
        background: brandColors.gradient,
        borderRadius: 16,
        padding: '24px 32px',
        marginBottom: 24,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => router.push('/construct/knowledge')}
            style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff' }}
          />
          <div className="flex items-center gap-3">
            <img src="/xsmartkg_logo.png" style={{ height: 48, objectFit: 'contain' }} alt="kg-docs" />
          </div>
        </div>
      </div>

      {/* 三栏布局 */}
      <Row gutter={24}>
        {/* 左栏：Graph Space 选择 */}
        <Col xs={24} lg={6}>
          <Card 
            title={<span><DatabaseOutlined /> Graph Spaces</span>}
            style={{ 
              borderRadius: 12, 
              background: brandColors.cardBg,
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
            }}
          >
            {loadingSpaces ? (
              <Spin />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {graphSpaces.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无图空间" />
                ) : (
                  graphSpaces.map(space => (
                    <div 
                      key={space}
                      onClick={() => {
                        setSelectedSpace(space);
                        form.setFieldValue('graph_space_name', space);
                      }}
                      style={{
                        padding: '12px 16px',
                        borderRadius: 8,
                        cursor: 'pointer',
                        background: selectedSpace === space 
                          ? 'linear-gradient(135deg, rgba(30, 136, 229, 0.15) 0%, rgba(38, 198, 218, 0.1) 100%)'
                          : '#f5f5f5',
                        border: selectedSpace === space ? `2px solid ${brandColors.primary}` : '2px solid transparent',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <Text strong={selectedSpace === space}>{space}</Text>
                    </div>
                  ))
                )}
              </div>
            )}
            
            <Divider style={{ margin: '16px 0' }} />
            
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <Text type="secondary" style={{ fontSize: 12 }}><HistoryOutlined /> 最近任务</Text>
                <Select 
                  size="small" 
                  defaultValue="all" 
                  style={{ width: 80, fontSize: 10 }}
                  onChange={(val) => setStatusFilter(val)}
                  options={[
                    { value: 'all', label: '全部' },
                    { value: 'running', label: '运行中' },
                    { value: 'completed', label: '已完成' },
                    { value: 'failed', label: '失败' },
                  ]}
                />
              </div>
              <div style={{ marginTop: 8 }}>
                {historyTasks.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无历史任务" />
                ) : (
                  historyTasks.slice(0, 5).map(task => (
                    <div 
                      key={task.task_id} 
                      style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        padding: '8px 0',
                        borderBottom: '1px solid #f0f0f0',
                        cursor: 'pointer'
                      }}
                      onClick={() => {
                        setSelectedTask(task);
                        setDrawerVisible(true);
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text ellipsis style={{ fontSize: 12, display: 'block' }}>{task.graph_space_name}</Text>
                        <Text type="secondary" style={{ fontSize: 10 }}>{task.entities_count} entities</Text>
                      </div>
                      <Tag color={task.status === 'completed' ? 'green' : task.status === 'failed' ? 'red' : 'blue'} style={{ fontSize: 10, marginLeft: 8 }}>
                        {task.status}
                      </Tag>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>
        </Col>

        {/* 中栏：上传和配置 */}
        <Col xs={24} lg={12}>
          <Card 
            title={<span><CloudUploadOutlined /> Upload & Configure</span>}
            style={{ 
              borderRadius: 12, 
              background: brandColors.cardBg,
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
            }}
          >
            <Form form={form} layout="vertical" initialValues={{ excel_mode: 'auto' }}>
              <Form.Item 
                name="graph_space_name" 
                label="Graph Space Name" 
                rules={[{ required: true, message: '请输入或选择图空间' }]}
              >
                <AutoComplete
                  placeholder="选择已有空间或输入新名称"
                  options={graphSpaces.map(s => ({ value: s, label: s }))}
                  onChange={(val) => setSelectedSpace(val)}
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item label="Processing Mode">
                <Radio.Group value={excelMode} onChange={(e) => setExcelMode(e.target.value)}>
                  <Radio.Button value="auto">🤖 Auto (LLM)</Radio.Button>
                  <Radio.Button value="mapping">📊 Column Mapping</Radio.Button>
                </Radio.Group>
              </Form.Item>

              {excelMode === 'mapping' && (
                <div style={{ 
                  background: 'linear-gradient(135deg, rgba(30, 136, 229, 0.05) 0%, rgba(38, 198, 218, 0.05) 100%)',
                  padding: 16, 
                  borderRadius: 8, 
                  marginBottom: 16,
                  border: '1px dashed rgba(30, 136, 229, 0.3)'
                }}>
                  <Text type="secondary" style={{ fontSize: 12, marginBottom: 12, display: 'block' }}>
                    配置 Excel 列到三元组的映射关系
                  </Text>
                  <Row gutter={12}>
                    <Col span={8}>
                      <Input 
                        placeholder="Subject 列" 
                        value={columnMapping.subjectColumn}
                        onChange={(e) => setColumnMapping({...columnMapping, subjectColumn: e.target.value})}
                      />
                    </Col>
                    <Col span={8}>
                      <Input 
                        placeholder="Predicate (关系)" 
                        value={columnMapping.predicate}
                        onChange={(e) => setColumnMapping({...columnMapping, predicate: e.target.value})}
                      />
                    </Col>
                    <Col span={8}>
                      <Input 
                        placeholder="Object 列" 
                        value={columnMapping.objectColumn}
                        onChange={(e) => setColumnMapping({...columnMapping, objectColumn: e.target.value})}
                      />
                    </Col>
                  </Row>
                </div>
              )}

              <Form.Item label="Extraction Prompt">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Select 
                    value={selectedPromptTemplate}
                    onChange={(val) => {
                      setSelectedPromptTemplate(val);
                      const template = PROMPT_TEMPLATES.find(t => t.key === val);
                      if (template) {
                        form.setFieldValue('custom_prompt', template.prompt);
                      }
                    }}
                    style={{ width: '100%' }}
                  >
                    {PROMPT_TEMPLATES.map(t => (
                      <Option key={t.key} value={t.key}>{t.label}</Option>
                    ))}
                  </Select>
                  <Form.Item name="custom_prompt" noStyle>
                    <Input.TextArea 
                      placeholder="选择模板或自定义实体关系提取的 Prompt..." 
                      rows={2} 
                    />
                  </Form.Item>
                </Space>
              </Form.Item>

              <Form.Item label="AWEL Workflow">
                <Button 
                  icon={<ReloadOutlined />} 
                  onClick={() => setAwelModalVisible(true)}
                  block
                  style={{ marginBottom: 16 }}
                >
                  {workflowConfig ? `✅ Workflow Configured` : '⚙️ Configure AWEL Workflow'}
                </Button>
              </Form.Item>

              <Dragger
                multiple
                accept=".txt,.md,.docx,.pdf,.xlsx,.xls"
                fileList={fileList}
                onRemove={(file) => {
                  const index = fileList.indexOf(file);
                  const newFileList = fileList.slice();
                  newFileList.splice(index, 1);
                  setFileList(newFileList);
                }}
                beforeUpload={(file) => {
                  const isLt50M = file.size / 1024 / 1024 < 50;
                  if (!isLt50M) {
                    message.error(`${file.name} 超过 50MB 限制`);
                    return Upload.LIST_IGNORE;
                  }
                  const allowedExts = ['.txt', '.md', '.docx', '.pdf', '.xlsx', '.xls'];
                  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
                  if (!allowedExts.includes(ext)) {
                    message.error(`${file.name} 是不支持的文件类型`);
                    return Upload.LIST_IGNORE;
                  }
                  
                  setFileList([...fileList, file]);
                  return false;
                }}
                style={{ borderColor: brandColors.primary }}
              >
                <p className="ant-upload-drag-icon" style={{ color: brandColors.primary }}>
                  <InboxOutlined style={{ fontSize: 48 }} />
                </p>
                <p className="ant-upload-text">拖拽或点击上传文件</p>
                <p className="ant-upload-hint">
                  支持: TXT, MD, DOCX, PDF, XLSX, XLS
                </p>
              </Dragger>

              <Button 
                type="primary" 
                size="large"
                block
                onClick={handleUpload} 
                loading={uploading}
                disabled={fileList.length === 0}
                style={{ 
                  marginTop: 24, 
                  height: 48,
                  background: brandColors.gradient,
                  border: 'none'
                }}
              >
                🚀 Start Building Knowledge Graph
              </Button>
            </Form>

            <Divider orientation="left" style={{ margin: '32px 0 16px' }}>Graph Preview (Thumbnail)</Divider>
            <GraphPreview spaceName={selectedSpace} refreshTrigger={graphRefresh} />
          </Card>
        </Col>

        {/* 右栏：进度监控 */}
        <Col xs={24} lg={6}>
          <Card 
            title={<span><BarChartOutlined /> Progress Monitor</span>}
            style={{ 
              borderRadius: 12, 
              background: brandColors.cardBg,
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
            }}
          >
            {taskId ? (
              <div style={{ textAlign: 'center' }}>
                {taskStatus === 'running' || taskStatus === 'pending' ? (
                  <LoadingOutlined style={{ fontSize: 48, color: brandColors.primary }} spin />
                ) : taskStatus === 'completed' ? (
                  <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
                ) : taskStatus === 'failed' ? (
                  <CloseCircleOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />
                ) : null}

                <Title level={4} style={{ marginTop: 16 }}>{taskStatus?.toUpperCase()}</Title>
                <Text type="secondary">{statusMsg || 'Initializing...'}</Text>

                <Progress 
                  percent={progress} 
                  strokeColor={brandColors.gradient}
                  style={{ marginTop: 16 }}
                />

                <div style={{ marginTop: 24, textAlign: 'left' }}>
                  <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>Task Queue</Text>
                  <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                    {taskFiles.map((file, idx) => (
                      <div key={idx} style={{ marginBottom: 12, padding: 8, background: '#f9f9f9', borderRadius: 4 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Text ellipsis style={{ maxWidth: 150, fontSize: 11 }}>{file.name}</Text>
                          <Tag color={file.status === 'completed' ? 'green' : file.status === 'processing' ? 'blue' : 'default'} style={{ fontSize: 9 }}>
                            {file.status}
                          </Tag>
                        </div>
                        <Progress percent={Math.floor((file.progress || 0) * 100)} size="small" strokeColor={brandColors.secondary} />
                      </div>
                    ))}
                    {taskFiles.length === 0 && (
                      <div style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>{fileList.length} files pending...</Text>
                      </div>
                    )}
                  </div>
                </div>

                <Row gutter={16} style={{ marginTop: 24 }}>
                  <Col span={12}>
                    <div style={{ 
                      padding: 16, 
                      borderRadius: 8, 
                      background: 'linear-gradient(135deg, rgba(30, 136, 229, 0.1) 0%, rgba(30, 136, 229, 0.05) 100%)'
                    }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: brandColors.primary }}>
                        <AnimatedCounter value={entitiesCount} />
                      </div>
                      <Text type="secondary" style={{ fontSize: 12 }}>Entities</Text>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div style={{ 
                      padding: 16, 
                      borderRadius: 8, 
                      background: 'linear-gradient(135deg, rgba(82, 196, 26, 0.1) 0%, rgba(82, 196, 26, 0.05) 100%)'
                    }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                        <AnimatedCounter value={relationsCount} />
                      </div>
                      <Text type="secondary" style={{ fontSize: 12 }}>Relations</Text>
                    </div>
                  </Col>
                </Row>

                <Space style={{ marginTop: 24 }}>
                  <Button onClick={resetTask}>Reset</Button>
                  {taskStatus === 'completed' && (
                    <Button 
                      type="primary"
                      style={{ background: brandColors.gradient, border: 'none' }}
                      onClick={() => {
                        const spaceName = form.getFieldValue('graph_space_name');
                        router.push(`/knowledge/graph?spaceName=${encodeURIComponent(spaceName)}`);
                      }}
                    >
                      View Graph →
                    </Button>
                  )}
                </Space>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
                <CloudUploadOutlined style={{ fontSize: 48, opacity: 0.3 }} />
                <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
                  上传文件后开始监控进度
                </Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 任务详情 Drawer */}
      <Drawer
        title={<span><HistoryOutlined /> Task Details</span>}
        placement="right"
        width={400}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
      >
        {selectedTask && (
          <div>
            <div style={{ marginBottom: 24 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Graph Space</Text>
              <Title level={4} style={{ margin: '4px 0' }}>{selectedTask.graph_space_name}</Title>
            </div>

            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={12}>
                <div style={{ 
                  padding: 16, 
                  borderRadius: 8, 
                  background: 'linear-gradient(135deg, rgba(30, 136, 229, 0.1) 0%, rgba(30, 136, 229, 0.05) 100%)',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: 28, fontWeight: 'bold', color: brandColors.primary }}>{selectedTask.entities_count}</div>
                  <Text type="secondary">Entities</Text>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ 
                  padding: 16, 
                  borderRadius: 8, 
                  background: 'linear-gradient(135deg, rgba(82, 196, 26, 0.1) 0%, rgba(82, 196, 26, 0.05) 100%)',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: 28, fontWeight: 'bold', color: '#52c41a' }}>{selectedTask.relations_count}</div>
                  <Text type="secondary">Relations</Text>
                </div>
              </Col>
            </Row>

            <Divider />

            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Status</Text>
              <div style={{ marginTop: 4 }}>
                <Tag color={selectedTask.status === 'completed' ? 'green' : selectedTask.status === 'failed' ? 'red' : 'blue'}>
                  {selectedTask.status.toUpperCase()}
                </Tag>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Progress</Text>
              <Progress percent={Math.floor(selectedTask.progress * 100)} strokeColor={brandColors.gradient} />
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Files</Text>
              <div style={{ marginTop: 4 }}>
                {selectedTask.file_names?.map((f: any, i: number) => (
                  <Tag key={i} style={{ marginBottom: 4 }}>{f.name}</Tag>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Created</Text>
              <div style={{ marginTop: 4 }}>{selectedTask.gmt_created}</div>
            </div>

            {selectedTask.completed_at && (
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>Completed</Text>
                <div style={{ marginTop: 4 }}>{selectedTask.completed_at}</div>
              </div>
            )}

            {selectedTask.error_message && (
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>Error</Text>
                <div style={{ marginTop: 4, color: '#ff4d4f' }}>{selectedTask.error_message}</div>
              </div>
            )}

            <Divider />

            <Space direction="vertical" style={{ width: '100%' }}>
              {selectedTask.status === 'completed' && (
                <Button 
                  type="primary" 
                  block
                  icon={<EyeOutlined />}
                  style={{ background: brandColors.gradient, border: 'none' }}
                  onClick={() => {
                    router.push(`/knowledge/graph?spaceName=${encodeURIComponent(selectedTask.graph_space_name)}`);
                  }}
                >
                  View Graph
                </Button>
              )}
              <Button 
                block
                icon={<ReloadOutlined />}
                onClick={() => {
                  form.setFieldValue('graph_space_name', selectedTask.graph_space_name);
                  setSelectedSpace(selectedTask.graph_space_name);
                  setDrawerVisible(false);
                  message.info('已加载配置，请选择文件后重新处理');
                }}
              >
                Reprocess
              </Button>
              <Button 
                block
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDeleteTask(selectedTask)}
              >
                Delete Task
              </Button>
            </Space>
          </div>
        )}
      </Drawer>

      <AWELWorkflowModal 
        visible={awelModalVisible} 
        onCancel={() => setAwelModalVisible(false)}
        onOk={(config) => setWorkflowConfig(config)}
      />
    </div>
  );
};

export default KGUploadPage;
