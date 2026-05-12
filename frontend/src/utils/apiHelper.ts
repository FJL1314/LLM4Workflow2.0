export function unwrapApiResponse<T = any>(res: any): {
  code: number;
  msg: string;
  data: T | null;
  raw: any;
} {
  if (res && typeof res === 'object' && 'data' in res) {
    const payload = res.data;

    if (payload && typeof payload === 'object' && 'code' in payload) {
      return {
        code: Number(payload.code ?? 500),
        msg: payload.msg ?? payload.message ?? 'request failed',
        data: (payload.data ?? null) as T | null,
        raw: payload,
      };
    }

    return {
      code: 200,
      msg: 'success',
      data: payload as T,
      raw: payload,
    };
  }

  if (res && typeof res === 'object' && 'code' in res) {
    return {
      code: Number(res.code ?? 500),
      msg: res.msg ?? res.message ?? 'request failed',
      data: (res.data ?? null) as T | null,
      raw: res,
    };
  }

  return {
    code: 200,
    msg: 'success',
    data: (res ?? null) as T | null,
    raw: res,
  };
}