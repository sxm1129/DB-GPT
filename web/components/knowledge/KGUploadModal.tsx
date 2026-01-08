import React, { useState, useEffect, useRef } from 'react';
import { Modal, Upload, Form, Input, Button, Progress, message, Space, List, Tag, Table, Radio, AutoComplete, Divider, Select, Collapse } from 'antd';
import { InboxOutlined, LoadingOutlined, CheckCircleOutlined, SyncOutlined, CloseCircleOutlined, PlusOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { uploadKGFiles, getKGTasks, getGraphSpaces, getPromptTemplates, KGTaskResponse, PromptTemplate, TemplateVariable } from '@/client/api/knowledge';
import { apiInterceptors } from '@/client/api';

const { Dragger } = Upload;
const { Option } = Select;
const { Panel } = Collapse;

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
  const [excelMode, setExcelMode] = useState<string>('auto');
  const [entitiesCount, setEntitiesCount] = useState<number>(0);
  const [relationsCount, setRelationsCount] = useState<number>(0);
  const [columnMapping, setColumnMapping] = useState<{
    subjectColumn: string;
    predicate: string;
    objectColumn: string;
  }>({ subjectColumn: '', predicate: '', objectColumn: '' });
  const [graphSpaces, setGraphSpaces] = useState<string[]>([]);
  const [loadingSpaces, setLoadingSpaces] = useState(false);
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (visible) {
      fetchHistory();
      fetchGraphSpaces();
      fetchTemplates();
    }
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [visible]);

  const fetchTemplates = async () => {
    try {
      const response = await getPromptTemplates({ include_system: true });
      // 后端API直接返回数据，不用apiInterceptors包装
      const data = response?.data as any;
      if (data && data.templates) {
        setTemplates(data.templates);
        if (data.templates.length > 0) {
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
    }
  };

  const handleTemplateChange = (templateId: number) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setSelectedTemplate(template);
      const defaults: Record<string, string> = {};
      template.variables?.forEach((v: TemplateVariable) => {
        if (v.default) defaults[v.name] = v.default;
      });
      setVariableValues(defaults);
    }
  };

  const getFinalPrompt = () => {
    if (!selectedTemplate) return '';
    let prompt = selectedTemplate.prompt_content;
    Object.entries(variableValues).forEach(([key, value]) => {
      prompt = prompt.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
    });
    return prompt;
  };

  const fetchGraphSpaces = async () => {
    setLoadingSpaces(true);
    try {
      const [err, res] = await getGraphSpaces();
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
    // 使用模板生成的 prompt
    const finalPrompt = getFinalPrompt();
    if (finalPrompt) {
      formData.append('custom_prompt', finalPrompt);
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
        if (data.entities_count !== undefined) setEntitiesCount(data.entities_count);
        if (data.relations_count !== undefined) setRelationsCount(data.relations_count);
        
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
            <AutoComplete
              placeholder="Select existing or type new name"
              options={graphSpaces.map(s => ({ value: s, label: s }))}
              filterOption={(inputValue, option) =>
                option?.value?.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
              }
              notFoundContent={loadingSpaces ? 'Loading...' : 'No existing spaces'}
            />
          </Form.Item>
          
          <Form.Item name="excel_mode" label="Processing Mode">
            <Radio.Group onChange={(e) => setExcelMode(e.target.value)}>
              <Radio value="auto">Auto (LLM Semantic Extraction)</Radio>
              <Radio value="mapping">Structured (Column Mapping)</Radio>
            </Radio.Group>
          </Form.Item>

          {excelMode === 'mapping' && (
            <div style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, marginBottom: 16 }}>
              <h4 style={{ margin: '0 0 12px 0' }}>Column Mapping Configuration</h4>
              <Form.Item label="Subject Column (Entity 1)" style={{ marginBottom: 8 }}>
                <Input 
                  placeholder="e.g., 公司名称" 
                  value={columnMapping.subjectColumn}
                  onChange={(e) => setColumnMapping({...columnMapping, subjectColumn: e.target.value})}
                />
              </Form.Item>
              <Form.Item label="Relation (Predicate)" style={{ marginBottom: 8 }}>
                <Input 
                  placeholder="e.g., 负责人是" 
                  value={columnMapping.predicate}
                  onChange={(e) => setColumnMapping({...columnMapping, predicate: e.target.value})}
                />
              </Form.Item>
              <Form.Item label="Object Column (Entity 2)" style={{ marginBottom: 0 }}>
                <Input 
                  placeholder="e.g., 负责人" 
                  value={columnMapping.objectColumn}
                  onChange={(e) => setColumnMapping({...columnMapping, objectColumn: e.target.value})}
                />
              </Form.Item>
            </div>
          )}

          <Form.Item label="提取模板">
            <Select 
              value={selectedTemplate?.id}
              onChange={handleTemplateChange}
              style={{ marginBottom: 12 }}
            >
              {templates.map(t => (
                <Option key={t.id} value={t.id}>
                  {t.is_system && '🔧 '}{t.name}
                </Option>
              ))}
            </Select>
            
            {selectedTemplate && selectedTemplate.variables && selectedTemplate.variables.length > 0 && (
              <Collapse size="small" style={{ marginBottom: 12 }}>
                <Panel header="模板变量配置" key="1">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                    {selectedTemplate.variables.map((v: TemplateVariable) => (
                      <div key={v.name} style={{ flex: '1 1 45%' }}>
                        <label style={{ fontSize: 12, color: '#666' }}>{v.description || v.name}</label>
                        {v.type === 'select' ? (
                          <Select
                            size="small"
                            value={variableValues[v.name]}
                            onChange={(val) => setVariableValues({...variableValues, [v.name]: val})}
                            style={{ width: '100%' }}
                          >
                            {v.options?.map(opt => (
                              <Option key={opt} value={opt}>{opt}</Option>
                            ))}
                          </Select>
                        ) : (
                          <Input
                            size="small"
                            value={variableValues[v.name]}
                            onChange={(e) => setVariableValues({...variableValues, [v.name]: e.target.value})}
                            placeholder={v.default}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                </Panel>
              </Collapse>
            )}
            
            <Input.TextArea 
              value={getFinalPrompt()}
              rows={3}
              readOnly
              style={{ background: '#f9f9f9', fontSize: 12 }}
              placeholder="最终提示词预览..."
            />
          </Form.Item>

          <Form.Item label="Files">
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
                setFileList([...fileList, file]);
                return false;
              }}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">Click or drag files to this area</p>
              <p className="ant-upload-hint">Supports: TXT, MD, DOCX, PDF, XLSX, XLS</p>
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
            
            <h3 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{taskStatus?.toUpperCase()}</h3>
            <p style={{ color: '#666', margin: 0 }}>{statusMsg || 'Initializing task...'}</p>
            
            <Progress 
              percent={progress} 
              status={taskStatus === 'failed' ? 'exception' : taskStatus === 'completed' ? 'success' : 'active'} 
              strokeWidth={12}
              strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
              style={{ maxWidth: 400, margin: '0 auto' }}
            />
            
            {/* 统计卡片 - Glassmorphism 风格 */}
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              gap: 24, 
              marginTop: 24,
            }}>
              <div style={{ 
                textAlign: 'center', 
                padding: '20px 32px', 
                borderRadius: 12,
                background: 'linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(24, 144, 255, 0.05) 100%)',
                border: '1px solid rgba(24, 144, 255, 0.2)',
                backdropFilter: 'blur(10px)',
              }}>
                <div style={{ fontSize: 32, fontWeight: 'bold', color: '#1890ff' }}>{entitiesCount}</div>
                <div style={{ color: '#666', marginTop: 4 }}>Entities</div>
              </div>
              <div style={{ 
                textAlign: 'center', 
                padding: '20px 32px', 
                borderRadius: 12,
                background: 'linear-gradient(135deg, rgba(82, 196, 26, 0.1) 0%, rgba(82, 196, 26, 0.05) 100%)',
                border: '1px solid rgba(82, 196, 26, 0.2)',
                backdropFilter: 'blur(10px)',
              }}>
                <div style={{ fontSize: 32, fontWeight: 'bold', color: '#52c41a' }}>{relationsCount}</div>
                <div style={{ color: '#666', marginTop: 4 }}>Relations</div>
              </div>
            </div>
            
            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center', gap: 12 }}>
              <Button onClick={() => { setTaskId(null); setUploading(false); setEntitiesCount(0); setRelationsCount(0); fetchHistory(); }}>
                Back
              </Button>
              {taskStatus === 'completed' && (
                <Button 
                  type="primary" 
                  onClick={() => {
                    const graphSpaceName = form.getFieldValue('graph_space_name');
                    window.location.href = `/knowledge/graph?spaceName=${encodeURIComponent(graphSpaceName)}`;
                  }}
                >
                  View Graph →
                </Button>
              )}
            </div>
          </Space>
        </div>
      )}
    </Modal>
  );
};

export default KGUploadModal;
