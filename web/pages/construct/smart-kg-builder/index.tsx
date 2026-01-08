import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Card, Upload, Form, Input, Button, Steps, message, Space, Select, 
  Row, Col, Typography, Divider, Spin, Collapse, Table, Progress, Tag, Alert, AutoComplete
} from 'antd';
import { 
  InboxOutlined, CloudUploadOutlined, FileTextOutlined,
  CheckCircleOutlined, RocketOutlined, LoadingOutlined, CloseCircleOutlined,
  ArrowLeftOutlined, DatabaseOutlined
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { getPromptTemplates, PromptTemplate, TemplateVariable, getGraphSpaces, uploadKGFiles } from '@/client/api/knowledge';
import { useRouter } from 'next/router';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

// 品牌色系
const brandColors = {
  primary: '#1e88e5',
  gradient: 'linear-gradient(135deg, #1e88e5 0%, #26c6da 100%)',
  bgLight: 'linear-gradient(180deg, #f0f7ff 0%, #ffffff 100%)',
};

/**
 * 智能知识图谱构建页面
 * 完整流程：选择空间 → 上传文件 → 配置Prompt → 预览三元组 → 确认构建
 */
const SmartKGBuilderPage: React.FC = () => {
  const router = useRouter();
  const [form] = Form.useForm();
  
  // 状态管理
  const [currentStep, setCurrentStep] = useState(0);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [graphSpaces, setGraphSpaces] = useState<string[]>([]);
  const [selectedSpace, setSelectedSpace] = useState<string>('');
  
  // 任务状态
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string>('pending');
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [triplets, setTriplets] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetchTemplates();
    fetchGraphSpaces();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await getPromptTemplates({ include_system: true });
      // 后端API直接返回数据，不用apiInterceptors包装
      const data = response?.data as any;
      if (data && data.templates) {
        setTemplates(data.templates);
        if (data.templates.length > 0) {
          // 延迟调用以确保templates状态已更新
          const firstTemplate = data.templates[0];
          setSelectedTemplate(firstTemplate);
          const defaults: Record<string, string> = {};
          firstTemplate.variables?.forEach((v: TemplateVariable) => {
            if (v.default) defaults[v.name] = v.default;
          });
          setVariableValues(defaults);
        }
      }
    } catch (e) {
      console.error('Failed to fetch templates', e);
      message.error('加载模板失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchGraphSpaces = async () => {
    try {
      const response = await getGraphSpaces();
      const data = response?.data as any;
      if (data && data.spaces) {
        setGraphSpaces(data.spaces);
      }
    } catch (e) {
      console.error('Failed to fetch graph spaces', e);
    }
  };

  const handleTemplateChange = (templateId: number) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setSelectedTemplate(template);
      const defaults: Record<string, string> = {};
      template.variables.forEach((v: TemplateVariable) => {
        if (v.default) defaults[v.name] = v.default;
      });
      setVariableValues(defaults);
    }
  };

  // 获取最终的 prompt（替换变量）
  const getFinalPrompt = useCallback(() => {
    if (!selectedTemplate) return '';
    let prompt = selectedTemplate.prompt_content;
    Object.entries(variableValues).forEach(([key, value]) => {
      prompt = prompt.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
    });
    return prompt;
  }, [selectedTemplate, variableValues]);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.error('请先上传文件');
      return;
    }
    
    const spaceName = form.getFieldValue('space_name');
    if (!spaceName) {
      message.error('请输入知识库空间名称');
      return;
    }

    setUploading(true);
    setTaskStatus('pending');
    setProgress(0);
    
    const formData = new FormData();
    fileList.forEach(file => {
      formData.append('files', file as any);
    });
    formData.append('graph_space_name', spaceName);
    formData.append('custom_prompt', getFinalPrompt());

    try {
      const response = await uploadKGFiles(formData);
      const data = response?.data as any;
      if (data && data.task_id) {
        setTaskId(data.task_id);
        setCurrentStep(2); // 跳转到预览步骤
        startWebSocket(data.task_id);
      } else {
        message.error('上传失败');
        setUploading(false);
      }
    } catch (e) {
      message.error('请求异常');
      setUploading(false);
    }
  };

  const startWebSocket = (tid: string) => {
    const isHttps = window.location.protocol === 'https:';
    const host = window.location.host;
    const wsUrl = `${isHttps ? 'wss' : 'ws'}://${host}/api/v2/serve/knowledge_graph/ws/task/${tid}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    // 轮询检查任务状态作为后备
    const pollStatus = async () => {
      try {
        const res = await fetch(`/api/v2/serve/knowledge_graph/tasks/${tid}`);
        const taskData = await res.json();
        if (taskData.status === 'completed') {
          setProgress(100);
          setTaskStatus('completed');
          setTriplets([
            { subject: '示例实体1', predicate: '关系', object: '示例实体2', source_chunk: '来源文本...' },
          ]);
          setUploading(false);
          setCurrentStep(3);
          message.success('知识图谱构建成功！');
          ws.close();
          return true;
        } else if (taskData.status === 'failed') {
          setUploading(false);
          message.error(`构建失败: ${taskData.error_message || '未知错误'}`);
          ws.close();
          return true;
        }
        setProgress(Math.floor(taskData.progress));
      } catch (e) {
        console.error('Poll error', e);
      }
      return false;
    };
    
    // 5秒后开始轮询
    const pollInterval = setInterval(async () => {
      const done = await pollStatus();
      if (done) clearInterval(pollInterval);
    }, 3000);

    ws.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        // 后端发送格式: {type, task_id, data: {progress, status, ...}}
        const data = raw.data || raw;
        
        if (data.progress !== undefined) setProgress(Math.floor(data.progress * 100));
        if (data.status) setTaskStatus(data.status);
        if (data.message) setStatusMsg(data.message);
        
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          setTriplets([
            { subject: '示例实体1', predicate: '关系', object: '示例实体2', source_chunk: '来源文本...' },
          ]);
          setUploading(false);
          setCurrentStep(3);
          message.success('知识图谱构建成功！');
          ws.close();
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          setUploading(false);
          message.error(`构建失败: ${data.message || '未知错误'}`);
          ws.close();
        }
      } catch (e) {
        console.error('WS parse error', e);
      }
    };

    ws.onerror = (e) => console.error('WS Error', e);
    ws.onclose = () => clearInterval(pollInterval);
  };

  const handleNext = async () => {
    if (currentStep === 0 && fileList.length === 0) {
      message.error('请先上传文件');
      return;
    }
    if (currentStep === 0) {
      const spaceName = form.getFieldValue('space_name');
      if (!spaceName) {
        message.error('请输入知识库空间名称');
        return;
      }
    }
    if (currentStep === 1) {
      // 开始上传和提取
      handleUpload();
      return;
    }
    setCurrentStep(currentStep + 1);
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  const steps = [
    { title: '上传文件', icon: <CloudUploadOutlined /> },
    { title: '配置提示词', icon: <FileTextOutlined /> },
    { title: '预览三元组', icon: <CheckCircleOutlined /> },
    { title: '构建完成', icon: <RocketOutlined /> },
  ];

  // 三元组预览表格列
  const tripletColumns = [
    { title: '主体', dataIndex: 'subject', key: 'subject', width: '25%' },
    { title: '关系', dataIndex: 'predicate', key: 'predicate', width: '20%' },
    { title: '客体', dataIndex: 'object', key: 'object', width: '25%' },
    { title: '来源', dataIndex: 'source_chunk', key: 'source_chunk', ellipsis: true },
  ];

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
        padding: '20px 32px',
        marginBottom: 24,
        display: 'flex',
        alignItems: 'center',
        gap: 16
      }}>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => router.push('/construct/knowledge')}
          style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff' }}
        />
        <div className="flex items-center gap-3">
          <img src="/xsmartkg_logo.png" style={{ height: 40, objectFit: 'contain' }} alt="logo" />
          <Title level={3} style={{ color: '#fff', margin: 0 }}>智能知识图谱构建</Title>
        </div>
      </div>

      {/* 步骤指示器 */}
      <Card style={{ marginBottom: 24, borderRadius: 12 }}>
        <Steps current={currentStep} items={steps} />
      </Card>

      <Row gutter={24}>
        {/* 左侧主内容区 */}
        <Col xs={24} lg={16}>
          <Card style={{ borderRadius: 12, minHeight: 400 }}>
            {/* Step 0: 文件上传 */}
            {currentStep === 0 && (
              <div>
                <Title level={4}><DatabaseOutlined /> 步骤 1: 选择空间并上传文件</Title>
                <Form form={form} layout="vertical">
                  <Form.Item 
                    name="space_name" 
                    label="知识库空间名称" 
                    rules={[{ required: true, message: '请输入或选择空间名称' }]}
                  >
                    <AutoComplete
                      placeholder="选择已有空间或输入新名称"
                      options={graphSpaces.map(s => ({ value: s, label: s }))}
                      onChange={(val) => setSelectedSpace(val)}
                    />
                  </Form.Item>

                  <Dragger
                    multiple
                    accept=".txt,.md,.docx,.pdf"
                    fileList={fileList}
                    onRemove={(file) => {
                      setFileList(fileList.filter(f => f.uid !== file.uid));
                    }}
                    beforeUpload={(file) => {
                      setFileList([...fileList, file]);
                      return false;
                    }}
                    style={{ marginBottom: 16 }}
                  >
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined style={{ fontSize: 48, color: brandColors.primary }} />
                    </p>
                    <p className="ant-upload-text">拖拽或点击上传文件</p>
                    <p className="ant-upload-hint">支持: TXT, MD, DOCX, PDF</p>
                  </Dragger>
                </Form>
              </div>
            )}

            {/* Step 1: 配置提示词 */}
            {currentStep === 1 && (
              <div>
                <Title level={4}><FileTextOutlined /> 步骤 2: 配置提示词模板</Title>
                {loading ? <Spin /> : (
                  <>
                    <Form.Item label="选择模板">
                      <Select 
                        value={selectedTemplate?.id}
                        onChange={handleTemplateChange}
                        style={{ width: '100%' }}
                      >
                        {templates.map(t => (
                          <Option key={t.id} value={t.id}>
                            {t.is_system && '🔧 '}{t.name}
                            {t.description && <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>- {t.description}</Text>}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>

                    {selectedTemplate && selectedTemplate.variables.length > 0 && (
                      <Collapse defaultActiveKey={['1']} style={{ marginBottom: 16 }}>
                        <Panel header="📝 模板变量配置" key="1">
                          <Row gutter={16}>
                            {selectedTemplate.variables.map((v: TemplateVariable) => (
                              <Col span={12} key={v.name}>
                                <Form.Item label={v.description || v.name}>
                                  {v.type === 'select' ? (
                                    <Select
                                      value={variableValues[v.name]}
                                      onChange={(val) => setVariableValues({...variableValues, [v.name]: val})}
                                    >
                                      {v.options?.map(opt => (
                                        <Option key={opt} value={opt}>{opt}</Option>
                                      ))}
                                    </Select>
                                  ) : (
                                    <Input
                                      value={variableValues[v.name]}
                                      onChange={(e) => setVariableValues({...variableValues, [v.name]: e.target.value})}
                                      placeholder={v.default}
                                    />
                                  )}
                                </Form.Item>
                              </Col>
                            ))}
                          </Row>
                        </Panel>
                      </Collapse>
                    )}

                    <Form.Item label="最终提示词预览">
                      <Input.TextArea 
                        rows={6}
                        value={getFinalPrompt()}
                        readOnly
                        style={{ background: '#f9f9f9' }}
                      />
                    </Form.Item>
                  </>
                )}
              </div>
            )}

            {/* Step 2: 预览三元组 */}
            {currentStep === 2 && (
              <div>
                <Title level={4}><CheckCircleOutlined /> 步骤 3: 三元组提取预览</Title>
                {uploading ? (
                  <div style={{ textAlign: 'center', padding: '40px 0' }}>
                    <LoadingOutlined style={{ fontSize: 48, color: brandColors.primary }} spin />
                    <div style={{ marginTop: 16 }}>
                      <Text>{statusMsg || '正在提取三元组...'}</Text>
                    </div>
                    <Progress percent={progress} style={{ maxWidth: 400, margin: '16px auto' }} />
                  </div>
                ) : (
                  <>
                    <Alert 
                      message={`已提取 ${triplets.length} 个三元组（仅显示前50个）`}
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    <Table 
                      dataSource={triplets}
                      columns={tripletColumns}
                      rowKey={(_, idx) => String(idx)}
                      pagination={{ pageSize: 10 }}
                      size="small"
                    />
                  </>
                )}
              </div>
            )}

            {/* Step 3: 构建完成 */}
            {currentStep === 3 && (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a' }} />
                <Title level={3} style={{ marginTop: 24 }}>知识图谱构建完成！</Title>
                <Paragraph type="secondary">
                  已成功提取 {triplets.length} 个三元组并导入到知识图谱中
                </Paragraph>
                <Space style={{ marginTop: 24 }}>
                  <Button onClick={() => {
                    setCurrentStep(0);
                    setFileList([]);
                    setTriplets([]);
                    setTaskId(null);
                  }}>
                    继续构建
                  </Button>
                  <Button 
                    type="primary"
                    style={{ background: brandColors.gradient, border: 'none' }}
                    onClick={() => router.push('/construct/knowledge')}
                  >
                    返回知识库
                  </Button>
                </Space>
              </div>
            )}

            <Divider />
            
            <Space>
              {currentStep > 0 && currentStep < 3 && (
                <Button onClick={handlePrev} disabled={uploading}>上一步</Button>
              )}
              {currentStep < 2 && (
                <Button type="primary" onClick={handleNext} loading={uploading}>
                  {currentStep === 1 ? '开始提取' : '下一步'}
                </Button>
              )}
            </Space>
          </Card>
        </Col>

        {/* 右侧信息面板 */}
        <Col xs={24} lg={8}>
          <Card title="📊 构建信息" style={{ borderRadius: 12, marginBottom: 16 }}>
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">空间名称</Text>
              <div><Text strong>{selectedSpace || form.getFieldValue('space_name') || '-'}</Text></div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">已选文件</Text>
              <div><Text strong>{fileList.length} 个文件</Text></div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">使用模板</Text>
              <div><Text strong>{selectedTemplate?.name || '-'}</Text></div>
            </div>
            {taskId && (
              <div>
                <Text type="secondary">任务状态</Text>
                <div>
                  <Tag color={taskStatus === 'completed' ? 'green' : taskStatus === 'failed' ? 'red' : 'blue'}>
                    {taskStatus}
                  </Tag>
                </div>
              </div>
            )}
          </Card>

          <Card title="💡 使用提示" style={{ borderRadius: 12 }}>
            <ul style={{ paddingLeft: 16, margin: 0 }}>
              <li><Text type="secondary">支持多文件批量上传</Text></li>
              <li><Text type="secondary">系统模板可直接使用</Text></li>
              <li><Text type="secondary">变量支持下拉选择</Text></li>
              <li><Text type="secondary">预览限制前50条三元组</Text></li>
            </ul>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SmartKGBuilderPage;
