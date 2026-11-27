import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Typography,
  message,
  type FormProps,
} from "antd";
import { LockOutlined, ReadOutlined, UserOutlined } from "@ant-design/icons";

import { ApiError } from "@/services/api";
import { useAuth } from "@/features/auth/AuthContext";

const { Title, Text } = Typography;

interface LoginFormValues {
  username: string;
  password: string;
}

export function LoginPage() {
  const { login } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit: FormProps<LoginFormValues>["onFinish"] = async (values) => {
    setSubmitting(true);
    setErrorMessage("");
    try {
      await login(values.username, values.password);
      message.success("Đăng nhập thành công.");
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Không thể đăng nhập. Vui lòng kiểm tra kết nối và thử lại.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-brand-panel">
        <div className="brand-lockup">
          <div className="brand-mark"><ReadOutlined /></div>
          <div>
            <div className="brand-name">HỆ THỐNG QUẢN LÝ</div>
            <div className="brand-caption">NHÀ SÁCH</div>
          </div>
        </div>

        <div className="brand-message">
          <Text className="eyebrow">HỆ THỐNG QUẢN LÝ NỘI BỘ</Text>
          <Title level={1}>Quản lý nhà sách, <span>đơn giản hơn.</span></Title>
          <Text className="brand-description">
            Một không gian làm việc tập trung cho bán hàng, kho, nhân sự và báo cáo.
          </Text>
        </div>

        <Text className="brand-footer">HỆ THỐNG QUẢN LÝ NHÀ SÁCH · WEB</Text>
      </section>

      <section className="login-form-panel">
        <Card className="login-card" bordered={false}>
          <div className="login-card-heading">
            <Text className="login-kicker">CHÀO MỪNG BẠN</Text>
            <Title level={2}>Đăng nhập</Title>
            <Text className="muted-text">
              Sử dụng tài khoản SQL Server được cấp cho nhân viên.
            </Text>
          </div>

          {errorMessage && (
            <Alert className="login-error" type="error" showIcon message={errorMessage} />
          )}

          <Form<LoginFormValues>
            layout="vertical"
            size="large"
            requiredMark={false}
            onFinish={handleSubmit}
            autoComplete="on"
          >
            <Form.Item
              label="Mã nhân viên"
              name="username"
              rules={[
                { required: true, message: "Vui lòng nhập mã nhân viên." },
                { max: 20, message: "Mã nhân viên không được vượt quá 20 ký tự." },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="Ví dụ: NV001"
                autoComplete="username"
                autoFocus
                maxLength={20}
              />
            </Form.Item>

            <Form.Item
              label="Mật khẩu"
              name="password"
              rules={[{ required: true, message: "Vui lòng nhập mật khẩu." }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Nhập mật khẩu SQL Server"
                autoComplete="current-password"
                maxLength={256}
              />
            </Form.Item>

            <Button className="login-submit" type="primary" htmlType="submit" block loading={submitting}>
              Đăng nhập hệ thống
            </Button>
          </Form>

          <div className="login-security-note">
            <LockOutlined />
            <Text className="muted-text">
              Phiên đăng nhập được bảo vệ và tự hết hạn theo cấu hình hệ thống.
            </Text>
          </div>
        </Card>
      </section>
    </main>
  );
}
