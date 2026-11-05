import type {NextConfig} from 'next';
const nextConfig:NextConfig={
  outputFileTracingIncludes:{'/api/*':['./cloud/backend.tar.gz']},
};
export default nextConfig;
